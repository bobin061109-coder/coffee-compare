package com.example.coffeehealth.health

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.PermissionController
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.ExerciseSessionRecord
import androidx.health.connect.client.records.HeartRateRecord
import androidx.health.connect.client.records.SleepSessionRecord
import androidx.health.connect.client.records.StepsRecord
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import java.time.Duration
import java.time.Instant
import java.time.temporal.ChronoUnit

/**
 * Health Connect 를 통해 갤럭시 워치(Samsung Health 동기화) 데이터를 읽는다.
 *
 * 전제: 사용자가 Samsung Health -> Health Connect 동기화를 켜두었고,
 *       아래 READ 권한에 동의한 상태.
 */
class HealthRepository(private val context: Context) {

    // 요청할 권한 집합 — 반드시 Manifest 선언과 일치해야 한다.
    val permissions = setOf(
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
    )

    private val client: HealthConnectClient
        get() = HealthConnectClient.getOrCreate(context)

    /** Health Connect 사용 가능 여부 (미설치/미지원 기기 대응) */
    fun availability(): Int =
        HealthConnectClient.getSdkStatus(context)   // SDK_UNAVAILABLE / _PROVIDER_UPDATE_REQUIRED / _AVAILABLE

    /** 권한 요청용 contract (Activity 에서 registerForActivityResult 로 사용) */
    fun requestPermissionsContract() =
        PermissionController.createRequestPermissionResultContract()

    suspend fun hasAllPermissions(): Boolean =
        client.permissionController.getGrantedPermissions().containsAll(permissions)

    /**
     * 추천에 필요한 '가공 전 원시 지표'를 모아 반환.
     * 이 중 민감하지 않은 feature 만 뽑아 서버로 보낸다.
     */
    suspend fun collectDailySignals(): HealthSignals {
        val now = Instant.now()
        val last24h = now.minus(24, ChronoUnit.HOURS)
        // 수면은 '어젯밤'을 보기 위해 36시간 창을 본다
        val last36h = now.minus(36, ChronoUnit.HOURS)

        return HealthSignals(
            lastNightSleepMinutes = readLastSleepMinutes(last36h, now),
            avgHeartRate = readAvgHeartRate(last24h, now),
            restingHeartRate = readMinHeartRate(last24h, now),
            steps = readSteps(last24h, now),
            recentExerciseMinutes = readExerciseMinutes(last24h, now),
        )
    }

    private suspend fun readLastSleepMinutes(start: Instant, end: Instant): Long? {
        val resp = client.readRecords(
            ReadRecordsRequest(
                recordType = SleepSessionRecord::class,
                timeRangeFilter = TimeRangeFilter.between(start, end),
            )
        )
        // 가장 최근(어젯밤) 세션
        val last = resp.records.maxByOrNull { it.endTime } ?: return null
        return Duration.between(last.startTime, last.endTime).toMinutes()
    }

    private suspend fun readAvgHeartRate(start: Instant, end: Instant): Int? {
        val resp = client.readRecords(
            ReadRecordsRequest(HeartRateRecord::class, TimeRangeFilter.between(start, end))
        )
        val bpms = resp.records.flatMap { it.samples }.map { it.beatsPerMinute }
        return if (bpms.isEmpty()) null else bpms.average().toInt()
    }

    private suspend fun readMinHeartRate(start: Instant, end: Instant): Int? {
        val resp = client.readRecords(
            ReadRecordsRequest(HeartRateRecord::class, TimeRangeFilter.between(start, end))
        )
        return resp.records.flatMap { it.samples }
            .minOfOrNull { it.beatsPerMinute }?.toInt()
    }

    private suspend fun readSteps(start: Instant, end: Instant): Long {
        val resp = client.readRecords(
            ReadRecordsRequest(StepsRecord::class, TimeRangeFilter.between(start, end))
        )
        return resp.records.sumOf { it.count }
    }

    private suspend fun readExerciseMinutes(start: Instant, end: Instant): Long {
        val resp = client.readRecords(
            ReadRecordsRequest(ExerciseSessionRecord::class, TimeRangeFilter.between(start, end))
        )
        return resp.records.sumOf {
            Duration.between(it.startTime, it.endTime).toMinutes()
        }
    }
}

/** Health Connect 에서 읽어낸 원시 지표 묶음 */
data class HealthSignals(
    val lastNightSleepMinutes: Long?,
    val avgHeartRate: Int?,
    val restingHeartRate: Int?,
    val steps: Long,
    val recentExerciseMinutes: Long,
)
