# 포함된 자료와 의존성

- **Pretendard** — Copyright Kil Hyung-jin / Adobe / Inter Project Authors. SIL Open Font License 1.1. [원문](licenses/Pretendard-OFL.txt), [원본 프로젝트](https://github.com/orioncactus/pretendard).
- **Vosk Android / Korean small model 0.22** — 음성 인식 서비스 연결 실패 시 사용하는 로컬 대체 엔진과 모델. [엔진](https://github.com/alphacep/vosk-api), [모델 배포·라이선스 표](https://alphacephei.com/vosk/models). Apache 2.0. 모델은 `./pleos setup`에서 공식 배포본을 받습니다.
- **Pleos Vehicle / NaviHelper / SpeechToText / TextToSpeech** — Pleos Playground 공식 Maven 배포 SDK. 각 SDK의 이용 조건을 따릅니다. 버전은 `android/app/build.gradle.kts`에 고정되어 있습니다.
- **AndroidX / Jetpack Compose / Kotlin / Coroutines / Gson / ML Kit / JNA** — Gradle 의존성으로 사용합니다. 개별 라이브러리의 라이선스가 적용됩니다.
- **Piper Korean KSS** — PC의 합성 음성 시험 전용 도구·모델입니다. APK에 포함하거나 런타임으로 사용하지 않습니다. [모델 카드](https://huggingface.co/rhasspy/piper-voices/blob/main/ko/ko_KR/kss/medium/MODEL_CARD)는 Bryan Park의 Korean Single Speaker Speech Dataset 및 CC BY-NC-SA 4.0을 명시합니다. `qa/native/fixtures/`의 합성 음성은 개발 검증 자료이며 제품용 음성 자산으로 사용하지 않습니다.

## 엣지 AI (차량 엣지 컴퓨터, APK 밖)

모델 파일은 저장소에 넣지 않고 [설치 가이드](manual/INSTALL.md)대로 공식 배포본을 받습니다.

- **Supertonic 3** (Supertone) — 플리의 기본 목소리. 엣지 GPU 합성과 헤드유닛 대체 엔진의 음성 팩(`scripts/build-tts-assets.py`). OpenRAIL-M.
- **SenseVoice Small** (FunAudioLLM, sherpa-onnx int8 변환본) — 엣지 음성 인식. 모델 라이선스는 [FunASR](https://github.com/modelscope/FunASR) 안내를 따릅니다. 추론 엔진 [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) Apache 2.0.
- **Kanana 1.5 2.1B Instruct** (Kakao, GGUF Q4_K_M) — 관찰을 아이 말투의 답으로 바꾸는 엣지 LLM. Apache 2.0. 추론 [llama.cpp](https://github.com/ggml-org/llama.cpp) MIT.
- **YuNet · SFace** ([OpenCV Zoo](https://github.com/opencv/opencv_zoo)) — 앨범의 얼굴 검출·신원 비교, 다른 아이 얼굴 흐림.
- **Qwen 비전 언어 모델** (GGUF, llama.cpp mtmd) — 앨범 사진 장면 설명. 각 모델 카드의 라이선스를 따릅니다.
- **faster-whisper** MIT — 캐시 음성의 받아쓰기 확인과 영상 대사 검사(개발 도구).
- **ONNX Runtime** MIT, **aiohttp**, **NumPy**, **OpenCV**, **Pillow**, **soundfile** — 버전은 `deploy/requirements-*.txt`.

## 데이터와 외부 서비스

- **OpenStreetMap** — 경로 주변 장소 오프라인 팩(`scripts/edge_data/places-*.json`). © OpenStreetMap contributors, ODbL.
- **Open-Meteo** — 현재 날씨·예보. 위치는 약 1km 단위로만 보냅니다. [이용 조건](https://open-meteo.com/en/licence).
- **MiniMax Speech 2.8 HD** (Figma Weave 경유) — 자주 하는 답을 미리 만들어 둔 상용 음성 녹음(`.tools/voice-cache`, 저장소 미포함). 서비스 이용 약관을 따릅니다. 실시간 경로에는 쓰지 않습니다.

## 제품 영상 제작 도구 (APK·런타임 미포함)

가족 장면은 영상 생성 모델(LTX-2, Seedance, OmniHuman, Kling AI Avatar, Nano Banana, Qwen-Image-Edit)로 만들고, PP-OCRv3·DiffuEraser·Real-ESRGAN·BiRefNet·Mask R-CNN으로 자막 제거·화질 개선·결함 검사를 했습니다. 기능 장면은 실제 Pleos 에뮬레이터 화면 녹화입니다. 각 모델과 서비스의 이용 조건을 따릅니다.

## 기타

플리 캐릭터와 화면 장식은 Compose Canvas 경로로 구현했습니다. 외부 캐릭터 이미지나 상용 일러스트를 포함하지 않습니다.

Tailscale 시연 서버는 PC에서만 `aiohttp`, `pulsectl`, `Pillow`, 시스템 `FFmpeg`를 사용합니다. APK의 의존성이 아닙니다. Python 패키지 버전은 `scripts/demo-requirements.txt`에 고정되어 있으며 각 배포 패키지의 라이선스가 적용됩니다. 브라우저 오디오와 중계 코드는 이 프로젝트에 포함됩니다. 영상은 실제 Pleos 에뮬레이터 화면이며 원격 마이크 음성 파일을 저장하지 않습니다.
