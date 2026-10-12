# Worship Lyrics Auto 5.0

VEGAS Pro용 찬양 가사 자동 싱크 테스트 버전입니다.

## 5.0에서 바뀐 핵심

4.x의 WhisperX 구간 추정/말소리 정렬 방식을 버리고, **MMS-300M 다국어 음향 모델 + 전체 가사 CTC Viterbi 강제정렬**로 교체했습니다.

- 곡마다 VEGAS 마커를 찍지 않습니다.
- 음악/영상 파일 + 정확한 가사 TXT만 넣습니다.
- Demucs로 보컬을 분리합니다.
- 한국어 가사를 uroman으로 음향 모델용 문자열로 변환합니다.
- 30초 오디오 창 + 2초 문맥으로 전체 곡의 음소 확률맵을 계산합니다.
- 이미 알고 있는 정답 가사를 전체 곡에 순서대로 강제정렬합니다.
- 가사 줄 사이의 `<star>` 상태가 전주/간주/호흡 같은 무가사 시간을 흡수합니다.
- 반복되는 Chorus도 TXT에 적힌 순서를 유지합니다.
- VEGAS 24fps/30fps Time & Frames TXT, SRT, CSV 리포트, MMS JSON을 출력합니다.

## 설치

폴더를 내려받은 뒤 `INSTALL_V5.bat`을 실행합니다.

설치가 끝나면 바탕화면의 **Worship Lyrics Auto 5.0**을 실행합니다.

첫 분석에서는 MMS 모델을 내려받기 때문에 시간이 더 걸립니다.

## 가사 TXT

기존처럼 섹션 태그를 쓸 수 있습니다.

```text
[Verse 1]
첫 번째 가사
두 번째 가사

[Chorus]
후렴 첫 줄
후렴 둘째 줄
```

섹션 태그가 없어도 동작하지만, 리포트 구분을 위해 사용하는 것을 권장합니다.

## 출력

- `*_VEGAS_TimeFrames_24fps.txt`
- `*_VEGAS_TimeFrames_30fps.txt`
- `*_SRT.srt`
- `*_SYNC_REPORT.csv`
- `*_MMS_ALIGNMENT.json`

VEGAS Pro 21에서는 **Insert → Insert Subtitles from Files...** 를 사용하고 저장해 둔 Titles & Text Preset을 선택합니다.

## 검증 원칙

5.0은 먼저 테스트 버전으로 운용합니다. 자동 생성 후 모든 가사 줄을 손으로 확인하는 대신 앞/중간/뒤와 프로그램 로그에 표시되는 MMS 점수가 낮은 5줄을 우선 확인합니다.

이 지점들이 안정적으로 맞으면 다음 곡으로 넘어갑니다. 특정 곡에서 어긋나면 자동 엔진을 개선하지, 곡마다 여러 마커를 찍는 방식으로 되돌아가지 않습니다.

## 캐시

- 앱: `%LOCALAPPDATA%\WorshipLyricsAuto5`
- 보컬 분리/모델 캐시: `%LOCALAPPDATA%\WorshipLyricsAuto5\cache`

같은 원본 파일을 다시 분석하면 보컬 분리 결과를 재사용합니다.

## 라이선스 주의

기본 정렬 모델 `MahmoudAshraf/mms-300m-1130-forced-aligner` 계열에는 **CC BY-NC 4.0(비상업)** 제한이 있습니다. 수익화/상업적 제작에 사용할 계획이라면 정렬 모델 라이선스를 별도로 확인하거나 상업 이용 가능한 모델로 교체해야 합니다.
