package com.example.coffeehealth.net

import com.example.coffeehealth.health.HealthSignals
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

/** 서버로 보내는 가공 feature. 원시 심박 배열/수면 세션 등은 전송하지 않는다. */
data class RecommendRequest(
    val sleepHours: Double?,
    val avgHeartRate: Int?,
    val restingHeartRate: Int?,
    val steps: Long,
    val exerciseMinutes: Long,
    val localHour: Int,                 // 현재 시각(0~23) — 카페인 컷오프 판단
)

data class RecommendResponse(
    val recommendation: String,
    val reason: String,
    val caffeineLimitMg: Int,
    val tags: List<String>,
)

fun HealthSignals.toRequest(): RecommendRequest = RecommendRequest(
    sleepHours = lastNightSleepMinutes?.let { it / 60.0 },
    avgHeartRate = avgHeartRate,
    restingHeartRate = restingHeartRate,
    steps = steps,
    exerciseMinutes = recentExerciseMinutes,
    localHour = java.time.LocalTime.now().hour,
)

interface RecommendService {
    @POST("/recommend")
    suspend fun recommend(@Body body: RecommendRequest): RecommendResponse
}

object RecommendApi {
    private const val BASE_URL = "https://api.your-coffee-brand.com"  // 교체
    val service: RecommendService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(MoshiConverterFactory.create())
            .build()
            .create(RecommendService::class.java)
    }
}
