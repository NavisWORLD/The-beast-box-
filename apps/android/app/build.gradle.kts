plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "dev.beastbox.mobile"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.beastbox.mobile"
        minSdk = 24
        targetSdk = 35
        versionCode = 700
        versionName = "0.7.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk { abiFilters += listOf("arm64-v8a", "x86_64") }
    }
    val keystorePath = System.getenv("BEASTBOX_ANDROID_KEYSTORE")
    if (!keystorePath.isNullOrBlank()) {
        signingConfigs {
            create("release") {
                storeFile = file(keystorePath)
                storePassword = System.getenv("BEASTBOX_ANDROID_KEYSTORE_PASSWORD") ?: ""
                keyAlias = System.getenv("BEASTBOX_ANDROID_KEY_ALIAS") ?: ""
                keyPassword = System.getenv("BEASTBOX_ANDROID_KEY_PASSWORD") ?: ""
            }
        }
    }
    buildTypes {
        getByName("debug") {
            isDebuggable = true
        }
        getByName("release") {
            isMinifyEnabled = false
            isDebuggable = false
            if (!keystorePath.isNullOrBlank()) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

chaquopy {
    defaultConfig { version = "3.12" }
    sourceSets {
        getByName("main") {
            // Package only public Python modules from this repository, plus our bridge.
            // This is the actual core source, not an Android reimplementation.
            srcDir("../../..")
            include("beastbox/**/*.py", "beast_android.py")
        }
    }
}

dependencies {
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}
