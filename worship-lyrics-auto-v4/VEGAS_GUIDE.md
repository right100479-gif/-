# VEGAS Pro 21 가져오기

4.0에서는 자막 스타일을 스크립트가 복사하지 않습니다. VEGAS 자체 Preset을 사용합니다.

1. 원하는 Titles & Text 자막 스타일을 하나 만듭니다.
2. Media Generator에서 Preset으로 저장합니다. 예: `찬양자막_기본`
3. **Insert → Insert Subtitles from Files...**
4. 24p 프로젝트는 `*_VEGAS_24fps.txt`
5. 30p 프로젝트는 `*_VEGAS_30fps.txt`
6. Preset에서 `찬양자막_기본` 선택
7. 확인
8. **Tools → Scripting → Worship_Fade_Imported_Subtitles**

이 흐름이 글꼴·위치·외곽선·그림자를 가장 안정적으로 유지합니다.
