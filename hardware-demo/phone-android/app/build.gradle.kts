plugins {
  id("com.android.application")
}

fun quoted(value: String): String = "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"") + "\""

android {
  namespace = "org.hackmit.memorypalace.phone"
  compileSdk = 36

  buildFeatures { buildConfig = true }

  defaultConfig {
    applicationId = "org.hackmit.memorypalace.phone"
    minSdk = 31
    targetSdk = 36
    versionCode = 1
    versionName = "1.0"
  }

  buildTypes {
    debug {
      buildConfigField(
          "String",
          "DEMO_BACKEND_URL",
          quoted(System.getenv("DEMO_BACKEND_URL") ?: "http://10.0.2.2:8771"),
      )
      buildConfigField(
          "String",
          "DEMO_TOKEN",
          quoted(System.getenv("DEMO_TOKEN") ?: ""),
      )
    }
    release {
      buildConfigField("String", "DEMO_BACKEND_URL", "\"\"")
      buildConfigField("String", "DEMO_TOKEN", "\"\"")
      isMinifyEnabled = false
      signingConfig = signingConfigs.getByName("debug")
    }
  }

  compileOptions {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
  }
}
