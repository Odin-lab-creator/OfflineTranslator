package com.example.offlinetranslator;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OnnxValue;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.nio.FloatBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Нейросетевой переводчик Opus-MT (MarianMT, Helsinki-NLP) в формате ONNX.
 * Токенизация SentencePiece (unigram) и жадное декодирование без кэша — без внешних библиотек,
 * кроме ONNX Runtime. Один экземпляр — одна пара языков (папка с моделью).
 */
public final class NeuralMt implements AutoCloseable {
    private static final String SPACE = "▁";

    private final OrtEnvironment env;
    private final OrtSession encoder;
    private final OrtSession decoder;
    private final HashMap<String, Float> scores = new HashMap<>();
    private final Set<String> userDefined = new HashSet<>();
    private final HashMap<String, Integer> vocab = new HashMap<>();
    private final String[] idToPiece;
    private final int maxPieceLength;
    private final float unknownScore;
    private final long pad;
    private final long eos;
    private final long unk;
    private final long start;
    private final int maxLength;

    private final String encIds;
    private final String encMask;
    private final String decIds;
    private final String decHidden;
    private final String decMask;

    public NeuralMt(File dir, int threads) throws IOException, OrtException {
        JSONObject config = new JSONObject(read(new File(dir, "config.json")));
        pad = config.getLong("pad");
        eos = config.getLong("eos");
        unk = config.optLong("unk", 1);
        start = config.optLong("decoder_start", pad);
        maxLength = config.optInt("max_length", 256);

        JSONObject vocabJson = new JSONObject(read(new File(dir, "vocab.json")));
        int maxId = 0;
        for (java.util.Iterator<String> it = vocabJson.keys(); it.hasNext(); ) {
            String piece = it.next();
            int id = vocabJson.getInt(piece);
            vocab.put(piece, id);
            if (id > maxId) maxId = id;
        }
        idToPiece = new String[maxId + 1];
        for (Map.Entry<String, Integer> e : vocab.entrySet()) idToPiece[e.getValue()] = e.getKey();

        JSONArray pieces = new JSONObject(read(new File(dir, "tokenizer.json"))).getJSONArray("pieces");
        float min = 0f;
        int maxLen = 1;
        for (int i = 0; i < pieces.length(); i++) {
            JSONArray p = pieces.getJSONArray(i);
            String piece = p.getString(0);
            float score = (float) p.getDouble(1);
            int type = p.optInt(2, 1);
            // 1 — обычный, 4 — пользовательский; служебные и неизвестный не участвуют в разбиении.
            if (type != 1 && type != 4) continue;
            scores.put(piece, score);
            if (type == 4) userDefined.add(piece);
            if (score < min) min = score;
            int length = piece.codePointCount(0, piece.length());
            if (length > maxLen) maxLen = length;
        }
        unknownScore = min - 10f;
        maxPieceLength = Math.min(maxLen, 32);

        env = OrtEnvironment.getEnvironment();
        OrtSession.SessionOptions options = new OrtSession.SessionOptions();
        options.setIntraOpNumThreads(Math.max(1, threads));
        options.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT);
        encoder = env.createSession(new File(dir, "encoder.onnx").getPath(), options);
        decoder = env.createSession(new File(dir, "decoder.onnx").getPath(), options);

        encIds = find(encoder.getInputNames(), "input_ids");
        encMask = find(encoder.getInputNames(), "attention_mask");
        decIds = find(decoder.getInputNames(), "input_ids");
        decHidden = find(decoder.getInputNames(), "encoder_hidden_states");
        decMask = find(decoder.getInputNames(), "attention_mask");
    }

    private static String read(File file) throws IOException {
        return new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8);
    }

    private static String find(Set<String> names, String part) {
        for (String name : names) if (name.equals(part)) return name;
        for (String name : names) if (name.contains(part)) return name;
        throw new IllegalStateException("в модели нет входа " + part + ": " + names);
    }

    // ---- SentencePiece (unigram) ----

    /** Разбивает текст на кусочки словаря (алгоритм Витерби, как в SentencePiece). */
    public List<String> pieces(String text) {
        String normalized = Normalizer.normalize(text, Normalizer.Form.NFKC).replaceAll("\\s+", " ").trim();
        if (normalized.isEmpty()) return new ArrayList<>();
        String s = SPACE + normalized.replace(" ", SPACE);
        int[] cps = s.codePoints().toArray();
        int n = cps.length;
        int[] offsets = new int[n + 1];
        for (int i = 0, off = 0; i < n; i++) {
            offsets[i] = off;
            off += Character.charCount(cps[i]);
            offsets[i + 1] = off;
        }
        float[] best = new float[n + 1];
        int[] from = new int[n + 1];
        boolean[] unknown = new boolean[n + 1];
        java.util.Arrays.fill(best, Float.NEGATIVE_INFINITY);
        best[0] = 0f;
        for (int end = 1; end <= n; end++) {
            for (int len = 1; len <= Math.min(maxPieceLength, end); len++) {
                int begin = end - len;
                if (best[begin] == Float.NEGATIVE_INFINITY) continue;
                String piece = s.substring(offsets[begin], offsets[end]);
                Float score = scores.get(piece);
                if (score == null) continue;
                // Пользовательские кусочки всегда выигрывают, как в SentencePiece.
                float value = best[begin] + (userDefined.contains(piece) ? 0f : score);
                if (value > best[end]) {
                    best[end] = value;
                    from[end] = begin;
                    unknown[end] = false;
                }
            }
            if (best[end] == Float.NEGATIVE_INFINITY && best[end - 1] != Float.NEGATIVE_INFINITY) {
                best[end] = best[end - 1] + unknownScore;
                from[end] = end - 1;
                unknown[end] = true;
            }
        }
        ArrayList<String> result = new ArrayList<>();
        int pos = n;
        while (pos > 0) {
            int begin = from[pos];
            result.add(0, s.substring(offsets[begin], offsets[pos]));
            pos = begin;
        }
        // Соседние неизвестные символы склеиваем, как SentencePiece.
        ArrayList<String> merged = new ArrayList<>();
        StringBuilder pending = null;
        for (String piece : result) {
            boolean isUnknown = !scores.containsKey(piece);
            if (isUnknown) {
                if (pending == null) pending = new StringBuilder();
                pending.append(piece);
            } else {
                if (pending != null) {
                    merged.add(pending.toString());
                    pending = null;
                }
                merged.add(piece);
            }
        }
        if (pending != null) merged.add(pending.toString());
        return merged;
    }

    public long[] encode(String text) {
        List<String> parts = pieces(text);
        int limit = Math.min(parts.size(), maxLength - 1);
        long[] ids = new long[limit + 1];
        for (int i = 0; i < limit; i++) {
            Integer id = vocab.get(parts.get(i));
            ids[i] = id == null ? unk : id;
        }
        ids[limit] = eos;
        return ids;
    }

    public String decode(List<Long> ids) {
        StringBuilder sb = new StringBuilder();
        for (long id : ids) {
            if (id == pad || id == eos) continue;
            String piece = id >= 0 && id < idToPiece.length ? idToPiece[(int) id] : null;
            if (piece == null) continue;
            if (id == unk) piece = "";
            sb.append(piece);
        }
        return sb.toString().replace(SPACE, " ").replaceAll(" +", " ").trim()
                .replace(" .", ".").replace(" ,", ",").replace(" !", "!").replace(" ?", "?");
    }

    // ---- Перевод ----

    /** Переводит одно предложение (жадный поиск). */
    public String translate(String sentence) throws OrtException {
        long[] ids = encode(sentence);
        if (ids.length <= 1) return "";
        long[][] input = new long[][]{ids};
        long[][] mask = new long[1][ids.length];
        for (int i = 0; i < ids.length; i++) mask[0][i] = 1;
        try (OnnxTensor inputTensor = OnnxTensor.createTensor(env, input);
             OnnxTensor maskTensor = OnnxTensor.createTensor(env, mask)) {
            HashMap<String, OnnxTensor> encInputs = new HashMap<>();
            encInputs.put(encIds, inputTensor);
            encInputs.put(encMask, maskTensor);
            try (OrtSession.Result encoded = encoder.run(encInputs)) {
                OnnxTensor hidden = (OnnxTensor) encoded.get(0);
                ArrayList<Long> out = new ArrayList<>();
                out.add(start);
                int limit = Math.min(maxLength, ids.length * 3 + 10);
                int repeats = 0;
                long last = -1;
                for (int step = 0; step < limit; step++) {
                    long[][] decoderInput = new long[1][out.size()];
                    for (int i = 0; i < out.size(); i++) decoderInput[0][i] = out.get(i);
                    long next;
                    try (OnnxTensor decTensor = OnnxTensor.createTensor(env, decoderInput)) {
                        HashMap<String, OnnxTensor> decInputs = new HashMap<>();
                        decInputs.put(decIds, decTensor);
                        decInputs.put(decHidden, hidden);
                        decInputs.put(decMask, maskTensor);
                        try (OrtSession.Result result = decoder.run(decInputs)) {
                            OnnxTensor logits = null;
                            for (Map.Entry<String, OnnxValue> e : result) {
                                if (e.getKey().equals("logits")) logits = (OnnxTensor) e.getValue();
                            }
                            if (logits == null) logits = (OnnxTensor) result.get(0);
                            long[] shape = logits.getInfo().getShape();
                            int vocabSize = (int) shape[shape.length - 1];
                            FloatBuffer buffer = logits.getFloatBuffer();
                            int offset = (out.size() - 1) * vocabSize;
                            float bestValue = Float.NEGATIVE_INFINITY;
                            long bestId = eos;
                            for (int v = 0; v < vocabSize; v++) {
                                if (v == pad) continue;
                                float value = buffer.get(offset + v);
                                if (value > bestValue) {
                                    bestValue = value;
                                    bestId = v;
                                }
                            }
                            next = bestId;
                        }
                    }
                    if (next == eos) break;
                    repeats = next == last ? repeats + 1 : 0;
                    last = next;
                    if (repeats > 6) break;
                    out.add(next);
                }
                out.remove(0);
                return decode(out);
            }
        }
    }

    @Override
    public void close() {
        try {
            encoder.close();
        } catch (Exception ignored) {
        }
        try {
            decoder.close();
        } catch (Exception ignored) {
        }
    }
}
