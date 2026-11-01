plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Номер сборки GitHub Actions становится versionCode, чтобы новые версии ставились поверх старых.
val ciVersionCode = (project.findProperty("ciVersionCode") as String?)?.toIntOrNull() ?: 1

// Постоянный ключ лежит в репозитории в зашифрованном виде; пароль хранится в секрете GitHub.
val signingPassword: String = System.getenv("SIGNING_KEY_PASSWORD").orEmpty()
val releaseKeystore = rootProject.file("keystore/release.p12")
val hasReleaseKey = signingPassword.isNotEmpty() && releaseKeystore.exists()

android {
    namespace = "com.example.offlinetranslator"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.offlinetranslator"
        minSdk = 23
        targetSdk = 35
        versionCode = ciVersionCode
        versionName = "1.$ciVersionCode"

        // Только ARM-процессоры (все современные телефоны) — APK становится в несколько раз меньше.
        ndk { abiFilters += listOf("arm64-v8a", "armeabi-v7a") }
    }

    packaging {
        // Сжимаем нативные библиотеки ML Kit внутри APK, чтобы файл быстрее скачивался.
        jniLibs { useLegacyPackaging = true }
    }

    signingConfigs {
        create("release") {
            if (hasReleaseKey) {
                storeFile = releaseKeystore
                storeType = "PKCS12"
                storePassword = signingPassword
                keyAlias = "valhalla"
                keyPassword = signingPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = if (hasReleaseKey) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("org.jsoup:jsoup:1.18.1")
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.exifinterface:exifinterface:1.3.7")

    // Камера
    val cameraX = "1.4.0"
    implementation("androidx.camera:camera-camera2:$cameraX")
    implementation("androidx.camera:camera-lifecycle:$cameraX")
    implementation("androidx.camera:camera-view:$cameraX")
    implementation("androidx.camera:camera-mlkit-vision:$cameraX")

    // Перевод, определение языка и распознавание текста на устройстве
    implementation("com.google.mlkit:translate:17.0.3")
    implementation("com.google.mlkit:language-id:17.0.6")
    implementation("com.google.mlkit:text-recognition:16.0.1")
    implementation("com.google.mlkit:text-recognition-chinese:16.0.1")
    implementation("com.google.mlkit:text-recognition-japanese:16.0.1")
    implementation("com.google.mlkit:text-recognition-korean:16.0.1")
    implementation("com.google.mlkit:digital-ink-recognition:19.0.0")
    // Кириллица на картинках
    implementation("cz.adaptech.tesseract4android:tesseract4android:4.9.0")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.8.1")
}
