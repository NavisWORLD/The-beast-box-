plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "dev.beastbox.device"
    compileSdk = 35
    defaultConfig {
        // Separate id from apps/android (dev.beastbox.mobile) so both can be installed side by side.
        applicationId = "dev.beastbox.device.experimental"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-experimental"
    }
    buildTypes {
        getByName("debug") { isDebuggable = true }
        getByName("release") { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    lint {
        abortOnError = true
        warningsAsErrors = false
        // The app is deliberately platform-only (no AppCompat); these are advisory for this experiment.
        disable += setOf("GradleDependency", "OldTargetApi", "AndroidGradlePluginVersion", "NewerVersionAvailable")
    }
    testOptions { unitTests.isReturnDefaultValues = true }
}

kotlin {
    compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
