pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven {
            url = uri("https://jitpack.io")
            content { includeGroup("cz.adaptech.tesseract4android") }
        }
    }
}
rootProject.name = "OfflineTranslator"
include(":app")
