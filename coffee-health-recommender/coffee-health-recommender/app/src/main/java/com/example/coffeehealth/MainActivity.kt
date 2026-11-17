package com.example.coffeehealth

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.foundation.layout.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.health.connect.client.HealthConnectClient
import androidx.lifecycle.lifecycleScope
import com.example.coffeehealth.health.HealthRepository
import com.example.coffeehealth.net.RecommendApi
import com.example.coffeehealth.net.toRequest
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private lateinit var repo: HealthRepository

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        repo = HealthRepository(this)

        // Health Connect 권한 요청 런처
        val permLauncher = registerForActivityResult(
            repo.requestPermissionsContract()
        ) { granted ->
            if (granted.containsAll(repo.permissions)) loadAndRecommend()
        }

        setContent {
            MaterialTheme {
                var status by remember { mutableStateOf("준비됨") }
                var result by remember { mutableStateOf<String?>(null) }

                // 화면에서 콜백이 상태를 갱신하도록 연결
                uiHook = { s, r -> status = s; r?.let { result = it } }

                Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("☕ 건강 기반 커피 추천", style = MaterialTheme.typography.headlineSmall)
                    Text("상태: $status")
                    Button(onClick = {
                        when (repo.availability()) {
                            HealthConnectClient.SDK_AVAILABLE ->
                                permLauncher.launch(repo.permissions)
                            else ->
                                status = "Health Connect 설치/업데이트가 필요합니다."
                        }
                    }) { Text("건강 데이터 연동하고 추천받기") }

                    result?.let { Card(Modifier.fillMaxWidth()) { Text(it, Modifier.padding(16.dp)) } }
                }
            }
        }
    }

    private fun loadAndRecommend() {
        lifecycleScope.launch {
            uiHook?.invoke("데이터 수집 중…", null)
            val signals = repo.collectDailySignals()
            uiHook?.invoke("추천 계산 중…", null)
            // 원시 데이터가 아닌 '가공 feature' 만 전송
            val resp = RecommendApi.service.recommend(signals.toRequest())
            val text = buildString {
                appendLine("추천: ${resp.recommendation}")
                appendLine("이유: ${resp.reason}")
                appendLine("권장 카페인 상한: ${resp.caffeineLimitMg}mg")
            }
            uiHook?.invoke("완료", text)
        }
    }

    companion object {
        // 데모 단순화를 위한 콜백. 실제 앱은 ViewModel/StateFlow 사용 권장.
        var uiHook: ((String, String?) -> Unit)? = null
    }
}
