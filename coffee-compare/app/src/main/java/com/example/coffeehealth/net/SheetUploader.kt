package com.example.coffeehealth.net

import com.example.coffeehealth.health.HealthSignals
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.time.Instant

/**
 * 워치에서 읽은 건강 지표를 '구글 시트'로 자동 전송한다.
 *
 * 가장 간단한 방법: Google Apps Script 웹앱(doPost)을 시트에 붙여,
 * 그 URL 로 JSON 을 POST 하면 시트에 한 줄(append)이 쌓인다.
 * (서비스계정 키를 앱에 넣지 않아도 되어 안전)
 *
 * --- Apps Script 쪽 코드(시트 > 확장 프로그램 > Apps Script 에 붙여넣고 '배포 > 웹앱') ---
 *   function doPost(e) {
 *     const d = JSON.parse(e.postData.contents);
 *     const sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
 *     sh.appendRow([d.timestamp, d.sleepHours, d.avgHeartRate,
 *                   d.restingHeartRate, d.steps, d.exerciseMinutes]);
 *     return ContentService.createTextOutput("ok");
 *   }
 * 배포 시 '액세스 권한: 모든 사용자' 로 설정하고, 나온 /exec URL 을 아래 WEBAPP_URL 에 넣는다.
 */
object SheetUploader {

    private const val WEBAPP_URL = "https://script.google.com/macros/s/배포ID/exec"  // 교체

    private val client = OkHttpClient()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    /** 백그라운드 스레드(코루틴 IO)에서 호출할 것 */
    fun upload(signals: HealthSignals) {
        val body = JSONObject().apply {
            put("timestamp", Instant.now().toString())
            put("sleepHours", signals.lastNightSleepMinutes?.let { it / 60.0 } ?: "")
            put("avgHeartRate", signals.avgHeartRate ?: "")
            put("restingHeartRate", signals.restingHeartRate ?: "")
            put("steps", signals.steps)
            put("exerciseMinutes", signals.recentExerciseMinutes)
        }.toString().toRequestBody(JSON)

        val req = Request.Builder().url(WEBAPP_URL).post(body).build()
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) throw RuntimeException("시트 업로드 실패: ${resp.code}")
        }
    }
}
