import com.example.offlinetranslator.NeuralMt;
import java.io.File;

public class NeuralTest {
    public static void main(String[] args) throws Exception {
        try (NeuralMt mt = new NeuralMt(new File(args[0]), 2)) {
            for (int i = 1; i < args.length; i++) {
                long t = System.currentTimeMillis();
                System.out.println("JAVA: " + args[i] + " => " + mt.translate(args[i]) + "  (" + (System.currentTimeMillis() - t) + " ms) pieces=" + mt.pieces(args[i]));
            }
        }
    }
}
