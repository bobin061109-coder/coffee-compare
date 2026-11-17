// app/build.gradle.kts — 필요한 의존성만 발췌
android {
    compileSdk = 35
    defaultConfig {
        minSdk = 28          // Health Connect 는 Android 9(API 28) 이상
        targetSdk = 35
    }
}

dependencies {
    // Health Connect
    implementation("androidx.health.connect:connect-client:1.1.0-rc03")

    // Jetpack Compose (UI)
    implementation(platform("androidx.compose:compose-bom:2024.09.03"))
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")

    // 네트워크
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.1")
}
