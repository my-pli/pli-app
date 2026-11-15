# 설치·실행 가이드

플리는 세 부분으로 실행합니다. **①만으로도 앱은 완전히 동작**하고, ②·③은 엣지 AI와 공개 시연을 더합니다.

| | 구성 | 결과 |
|---|---|---|
| ① | Pleos Connect 2.1 에뮬레이터 + 플리 APK | 음성 놀이·일정·차량 신호·쉿·길 안내 양보 (헤드유닛 음성 엔진) |
| ② | 차량 엣지 AI (LLM · 에이전트 · 음성) | 자유 질문, 먼저 제안, 이야기 앨범, 생기 있는 목소리, EDGE AGENT 단계 |
| ③ | 시연 포털 · 공개 터널 | 브라우저에서 앱 체험·Pleos 조작·영상 |

---

## 0. 요구 사항

| 항목 | 기준 |
|---|---|
| OS | Linux x86_64 (Ubuntu 24.04 LTS에서 검증) |
| 가상화 | KVM (`/dev/kvm` 읽기·쓰기 권한) |
| 도구 | JDK 17, Python 3.12, curl, FFmpeg, 그래픽·오디오 세션 |
| 디스크 | 앱 ① 약 30GB (Android SDK·에뮬레이터·Pleos 이미지), 엣지 ② 약 6GB (+ 선택 모델 3GB) |
| GPU | 선택. 엣지 음성(Supertonic 3 CUDA)과 에뮬레이터 호스트 GPU 렌더링에 사용. 검증: RTX 4070 노트북 GPU |

모든 도구·SDK·모델은 저장소 안의 `.tools/`에 설치되며, 시스템 전역 설정을 바꾸지 않습니다.

---

## 1. 앱 — Pleos 에뮬레이터 + APK

```sh
./pleos setup            # Android SDK 35 · 에뮬레이터 35.6.11 · 공식 Pleos Connect 2.1 이미지(체크섬 검증) · 한국어 대체 인식 모델 · 개발 서명 키
./pleos doctor           # Java 17 · Android SDK · Pleos 이미지 · 한국어 모델 · KVM 확인
./pleos test             # 단위 테스트 78개 (Gradle :app:testDebugUnitTest)
./pleos run --release    # 릴리스 빌드 → 에뮬레이터 기동 → 설치 → 마이크 권한 → 실행
```

| 명령 | 하는 일 |
|---|---|
| `./pleos build --release` | `artifacts/pli-pleos.apk` 생성 (패키지 `ai.teammoon.pli`, 3.2.0) |
| `./pleos --profile personal run --release` | 개인용 Pleos (가족 자료) |
| `./pleos --profile public run --release` | 공개용 Pleos (샘플 자료만) |
| `./pleos state` | 앱의 현재 상태(JSON) |
| `./pleos screenshot [경로]` | 화면 캡처 (기본 `qa/native/screen.png`) |
| `./pleos say "내일 뭐 챙겨?"` · `./pleos event rain` | 개발 APK 전용 입력 주입 (실제 음성 인식 시험과 구분). 차량 이벤트: `depart` `arrive` `rain` `charging` `door_open` `navigation_start` `navigation_end` |
| `./pleos import-plan /절대/경로/계획안.jpg` | 놀이계획안 사진·TXT/CSV를 기기로 전달 (바이트 검증) |
| `./pleos stop` | 이 프로젝트의 에뮬레이터와 개발 콘솔 세션 종료 |

실행 중에는 Pleos Virtual Console(`http://127.0.0.1:8088/`)에서 차량 값을 바꿔 볼 수 있습니다. `./pleos run`이 포트 전달과 콘솔 세션을 함께 준비합니다.

**빌드 없이 설치 · 다른 Pleos 기기에 설치**

저장소의 배포용 APK(Git LFS)를 그대로 설치할 수 있습니다. 직접 빌드했다면 `artifacts/pli-pleos.apk`를 씁니다.

```sh
git lfs install && git lfs pull          # 복제본에 APK 실제 파일 받기
adb install -r "apk/플리_pli_release.apk" # 3.2.0 · SHA-256 4a083908…1257b9
```

처음 실행할 때 Android의 마이크 권한 허용이 한 번 필요합니다. 앱은 엣지가 없어도 헤드유닛 안의 음성 엔진과 규칙으로 동작합니다.

---

## 2. 차량 엣지 AI

에뮬레이터 안의 앱은 호스트를 `10.0.2.2`로 봅니다. 즉 개발 PC가 **차량 엣지 컴퓨터** 역할을 합니다. 모든 서비스는 루프백(127.0.0.1)에서만 열립니다.

| 서비스 | 포트 | 역할 |
|---|---|---|
| `pli-edge-llm` | 8891 | llama.cpp 서버 · Kanana 1.5 2.1B (CPU) |
| `pli-edge-ai` | 8890 | 음성 인식(SenseVoice) · 에이전트 루프 · 장소·날씨 · 놀이 · 앨범 |
| `pli-edge-voice` | 8892 | 플리 목소리 (Supertonic 3 GPU + 생기 있는 답 캐시) · 헤드유닛 음성 팩 배포 |

### 2.1 가상환경

```sh
python3 -m venv .tools/edge-venv
.tools/edge-venv/bin/pip install -r deploy/requirements-edge.txt supertonic==1.3.1

python3 -m venv .tools/tts-gpu-venv            # CUDA 12 · cuDNN 9
.tools/tts-gpu-venv/bin/pip install -r deploy/requirements-voice.txt

python3 -m venv .tools/tts-build-venv          # 음성 팩 빌드 전용
.tools/tts-build-venv/bin/pip install onnx==1.17.0 onnxruntime==1.22.1 numpy==2.5.4
```

### 2.2 모델 배치

공식 배포본을 받아 아래 위치에 둡니다(라이선스는 [THIRD-PARTY](../THIRD-PARTY.md)).

```text
.tools/edge-ai/
├── bin/llama-b12314/                         llama.cpp b12314 릴리스 (llama-server, llama-mtmd-cli)
└── models/
    ├── asr/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/   sherpa-onnx ASR 모델 릴리스 (230MB)
    ├── kanana-1.5-2.1b/kakaocorp.kanana-1.5-2.1b-instruct-2505.Q4_K_M.gguf   (1.5GB)
    ├── face/face_detection_yunet_2023mar.onnx                          OpenCV Zoo
    ├── face/face_recognition_sface_2021dec.onnx                        OpenCV Zoo
    └── Qwen3.5-4B-GGUF/ (Q4_K_M + mmproj)                              앨범 장면 설명 (선택, 3.2GB)
```

플리의 목소리(Supertonic 3, 보이스 F3)는 한 번 받아 음성 팩으로 만듭니다.

```sh
.tools/edge-venv/bin/python -c "from supertonic import TTS; TTS(auto_download=True)"   # ~/.cache/supertonic3
.tools/tts-build-venv/bin/python scripts/build-tts-assets.py --voice F3                 # → .tools/voice-pack (192MB)
```

`build-tts-assets.py`는 fp32 원본과 fp16 저장 팩을 같은 문장으로 합성해 비교하고, 들리는 차이가 있으면(log-mel 거리) 아무것도 쓰지 않습니다. 현재 팩의 차이는 0.055dB입니다.

### 2.3 서비스 설치와 확인

```sh
deploy/install-edge-services.sh
```

필요한 파일이 없으면 무엇이 빠졌는지 알려 주고 멈춥니다. 성공하면 세 서비스를 systemd 사용자 서비스로 등록·시작하고 상태를 확인합니다.

```text
ok    pli-edge-llm   http://127.0.0.1:8891/health
ok    pli-edge-ai    http://127.0.0.1:8890/v1/health
ok    pli-edge-voice http://127.0.0.1:8892/v1/voice/health
```

```sh
curl -s http://127.0.0.1:8890/v1/health
# {"ok": true, "asr": {"engine": "sensevoice", "ready": true, "p50Ms": 168}, "llm": {"ready": true, ...}, "album": {...}}
```

### 2.4 이야기 앨범 준비 (선택)

```sh
.tools/edge-venv/bin/python scripts/family_photos.py --describe --input <비공개 사진 폴더>
```

아이 얼굴을 특정하고, 다른 얼굴을 흐리고, EXIF를 지운 사본과 장면 설명을 `.tools/edge-ai/family-album`에 만듭니다. 원본 사진은 비공개 폴더(권한 700/600)에만 두며 APK·저장소·공개 자료에 넣지 않습니다.

### 2.5 생기 있는 답 캐시 (선택)

자주 하는 답을 미리 만든 녹음으로 들려줍니다. 서버는 요청 문장의 `sha256(text)[:24]`로 `.tools/voice-cache/<key>.wav`(44.1kHz 모노 16bit)를 찾고, 없으면 Supertonic 3으로 즉시 합성한 뒤 그 문장을 `queue.jsonl`에 남깁니다. 응답 헤더 `X-Voice-Source`가 `expressive-cache` 또는 `supertonic`을 알려 줍니다.

```sh
# 후보 녹음(.tools/voice-cache/candidates/<key>-*.wav, <key>.txt)을 받아쓰기·음질·생동감으로 골라 제공 파일로
.tools/edge-venv/bin/python scripts/edge_voice_cache_pick.py [--source mm]
```

### 2.6 가족 서비스 MCP (선택)

개인 계정의 일정·앨범을 읽는 MCP 서버는 루프백 · 베어러 토큰 · 읽기 전용으로 동작하며, 계정 정보는 `.tools/private/`에만 둡니다. 공개 시연은 이 연결 없이 샘플 자료로 동작합니다.

---

## 3. 시연 포털 · 공개 터널

```sh
./pleos demo start        # 개인 시연 포털 (http://127.0.0.1:8876, 가족 연결 /family)
./pleos public start      # 공개용 Pleos + 포털 + HTTPS 터널
./pleos public status     # 현재 공개 주소
./pleos public stop
```

| 프로필 | 포털 HTTP / HTTPS | 용도 |
|---|---|---|
| personal | 8876 / 8877 | 가족 자료, 가족 연결 페이지 |
| public | 8878 / 8879 | 샘플 자료만, 한 명씩 3분 체험 + 관람 |

포털은 `/app`(실제 앱 View), `/pleos`(시스템 바·독·차량 3D를 포함한 display 0), `/resources`(영상·기획서·APK)를 제공합니다. 웹 자산만 바꿨다면 `python3 scripts/build-portal-assets.py --publish`로 반영합니다.

---

## 4. 검사

```sh
./pleos test                                          # 단위 78개
python3 qa/native/run-acceptance.py                   # 인수 검사 27종의 계획만 표시 (기기를 띄우지 않음)
python3 qa/native/run-acceptance.py --only fast-unit  # 선택 실행
python3 qa/native/run-acceptance.py --only edge-ai    # 엣지 ASR 정확도·지연, 플래너, 근거 있는 답, 안전, 앨범
python3 qa/native/run-acceptance.py --full            # 전체 (기기·포털 포함, 오래 걸림)
```

검사 기록은 `qa/native/runs/`(저장소 제외)에 남고, 입력 파일·고정 음성의 해시로 결과와 소스를 묶습니다. 고정 음성(`qa/native/fixtures/*.wav`)은 모두 합성 음성이며 실제 사람 녹음이 아닙니다.

---

## 5. 문제 해결

| 증상 | 해결 |
|---|---|
| `KVM: False` | 사용자를 `kvm` 그룹에 추가하고 다시 로그인 |
| `공식 Pleos 이미지 체크섬이 일치하지 않습니다` | `.tools/downloads/pleos-connect-2.1.0.zip`을 지우고 `./pleos setup` 재실행 |
| 에뮬레이터 화면이 느림 | 공개 프로필은 NVIDIA 드라이버가 있으면 외장 GPU를 씁니다. 비교: `PLI_HOST_GPU=nvidia` / `PLI_HOST_GPU=default`로 해당 프로필을 새로 기동. 실제 renderer는 프로필의 `logs/emulator.log`에 기록 |
| 앱이 엣지를 못 찾음 | `curl http://127.0.0.1:8890/v1/health` 확인. 앱은 `10.0.2.2:8890`(에이전트)·`:8892`(음성)으로 접속합니다. 엣지가 없으면 앱은 헤드유닛 엔진으로 자동 전환합니다 |
| 엣지 음성이 CPU로 돌아감 | `tts-gpu-venv`의 onnxruntime-gpu가 CUDA 12·cuDNN 9를 찾는지 확인 (`/v1/voice/health`의 `provider`가 `CUDAExecutionProvider`) |
| 서비스 로그 | `journalctl --user -u pli-edge-ai -f` |
| 이 프로젝트만 정리 | `./pleos stop` (다른 에뮬레이터·프로젝트는 건드리지 않음) |

더 알아보기: [사용 설명서](USER-GUIDE.md) · [기술 문서](ARCHITECTURE.md) · [심사 시연 가이드](DEMO-GUIDE.md)
