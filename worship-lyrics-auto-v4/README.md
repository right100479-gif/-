# Worship Lyrics Auto 4.0

찬양 음원/영상과 정확한 가사 TXT를 넣으면, 보컬을 분리한 뒤 한국어 강제정렬을 이용해 VEGAS Pro용 자막 타이밍 파일을 만드는 Windows 프로그램입니다.

## 왜 4.0인가

이 버전은 완성 음원 전체를 그대로 Whisper에 맡겨 받아쓴 문장을 다시 가사와 맞추는 방식에서 벗어납니다.

1. **Demucs**로 보컬을 먼저 분리합니다.
2. 분리된 보컬에서 **WhisperX**가 Verse / Chorus / Bridge 같은 구간의 대략적 위치를 찾습니다.
3. 각 구간을 짧은 창으로 나눈 뒤, **한국어 wav2vec2 CTC 강제정렬**로 사용자가 입력한 정확한 가사를 직접 맞춥니다.
4. 반복되는 Chorus / Final Chorus도 TXT에 적힌 순서대로 별도 구간으로 처리합니다.
5. VEGAS 스타일은 스크립트가 흉내 내지 않고 **VEGAS 자체 Preset**을 사용합니다.

이 구조는 테스트 기준 가사처럼 Verse, Chorus, Bridge, Final Chorus, Outro가 반복되는 찬양을 염두에 두고 만들었습니다.

## 설치

1. 이 폴더를 ZIP으로 내려받아 완전히 압축 해제합니다.
2. `INSTALL_V4.bat`을 실행합니다.
3. `INSTALL COMPLETE`가 나오면 바탕화면의 **Worship Lyrics Auto 4.0**을 실행합니다.
4. VEGAS Pro 21에서 **Tools → Scripting → Rescan Script Menu Folder**를 한 번 실행합니다.

첫 설치/첫 분석에서는 Python 패키지와 AI 모델을 다운로드하므로 시간이 꽤 걸릴 수 있습니다.

## 가사 TXT 형식

구간 제목을 대괄호로 적고 그 아래 가사를 한 줄씩 적습니다.

~~~text
[Verse 1]
첫 번째 가사
두 번째 가사

[Chorus]
후렴 첫 줄
후렴 둘째 줄

[Bridge]
브리지 첫 줄
~~~

같은 `[Chorus]`가 여러 번 나와도 괜찮습니다. **파일에 적힌 순서대로 각각 다른 구간으로 처리**합니다.

## 평소 사용

1. 음악/영상 파일을 위쪽 칸에 끌어놓습니다.
2. 정확한 가사 TXT를 아래쪽 칸에 끌어놓습니다.
3. 결과 폴더를 확인합니다.
4. **자동 싱크 생성 시작**을 누릅니다.
5. 완료 후 결과 폴더에서 VEGAS용 TXT를 사용합니다.

생성 파일:

- `*_VEGAS_24fps.txt`
- `*_VEGAS_30fps.txt`
- `*_SRT.srt`
- `*_SYNC_REPORT.csv`
- `*_VEGAS_불러오기.txt`

## VEGAS Pro 21에서 불러오기

프로젝트가 24.000p이면 `*_VEGAS_24fps.txt`, 30.000p이면 `*_VEGAS_30fps.txt`를 사용합니다.

1. VEGAS 상단 **Insert**
2. **Insert Subtitles from Files...**
3. 생성된 TXT 선택
4. **Preset**에서 사용자가 저장해 둔 찬양 자막 스타일 선택
5. 확인

이 방식은 VEGAS 자체 Preset으로 Titles & Text 이벤트를 생성하므로 글꼴, 글자 크기, 위치, 정렬, 외곽선, 그림자 등이 이전 스크립트 복사 방식보다 안정적입니다.

## 페이드 인/아웃

자막을 가져온 다음:

**Tools → Scripting → Worship_Fade_Imported_Subtitles**

를 실행하면 Titles & Text 이벤트에 0.25초 Smooth Fade In/Out을 적용합니다.

## Preset 한 번 저장하기

1. 기존에 원하는 모양의 Titles & Text 자막 하나를 엽니다.
2. Media Generator의 Preset 이름 칸에서 예를 들어 `찬양자막_기본`으로 저장합니다.
3. 이후 **Insert Subtitles from Files...**에서 이 Preset을 선택합니다.

## 요구 환경

- Windows 10/11
- VEGAS Pro 21
- Python 3.11
- FFmpeg
- 인터넷 연결: 최초 모델 다운로드 시 필요
- NVIDIA GPU가 있으면 자동으로 CUDA를 사용하려 시도하고, 없으면 CPU로 동작합니다.

## 주의

자동 정렬은 노래의 발음, 애드리브, 코러스 중첩, 악기 누출 정도에 따라 일부 줄이 어긋날 수 있습니다. 프로그램은 구간별 직접 CTC 정렬 비율을 `SYNC_REPORT.csv`에 남깁니다. 낮은 신뢰도 구간은 VEGAS에서 마지막 확인을 권장합니다.

사용자가 넣은 가사 문장은 프로그램이 임의로 고치지 않습니다.
