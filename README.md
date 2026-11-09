# 초록도감 · 로컬 식물 분류 웹앱

사진으로 실내 식물 후보를 살펴보는 Python/FastAPI + HTML/CSS/JavaScript 웹앱입니다. Windows의 일반 PowerShell에서 설치된 Python으로 실행합니다. 이미지 업로드·드래그 앤 드롭·미리보기·상위 후보 3개·오류 안내를 제공합니다.

분석은 내 컴퓨터의 CPU에서 수행하며 사진을 저장하거나 외부 추론 서비스에 전송하지 않습니다. **결과는 47개 학습 범주 안의 추정치**입니다. 모델 점수는 정답 확률이나 정확도를 의미하지 않습니다.

## 사용 환경

- Windows 11, Python 3.14 x64, pip. 실제 실행은 Python 3.14.8에서 확인했습니다.
- INT8 ONNX 모델과 최대 4개 CPU 스레드를 사용합니다. GPU나 PyTorch가 필요하지 않습니다.
- 가상환경, 관리자 권한, PATH 수정, PowerShell 실행 정책 변경이 필요하지 않습니다.
- 최초 패키지 설치와 모델 다운로드에는 인터넷 연결이 필요하며, 준비 후 분석은 오프라인으로 동작합니다.

## 설치 방법

이 저장소를 clone하거나 ZIP으로 내려받아 압축을 푼 뒤, PowerShell에서 프로젝트 폴더로 이동합니다. 아래 `HW2`는 내려받은 폴더 이름에 맞춰 변경하세요.

```powershell
cd .\HW2
python --version
python -m pip --version
python -m pip install --target .packages -r requirements.txt
```

`.packages`는 프로젝트 안의 패키지 폴더이며 가상환경이 아닙니다. `run.py`가 이 폴더를 우선 사용하므로 다른 프로젝트의 패키지를 변경하지 않습니다. `requirements.txt`에는 실제 사용한 직접·간접 의존성 21개의 버전을 고정했습니다. 설치가 성공했고 파일이 그대로라면 설치 명령을 반복할 필요가 없습니다.

## 모델 준비 방법

프로젝트 폴더에서 다음 명령을 실행합니다.

```powershell
python prepare_model.py
```

약 87MB의 모델과 라벨·전처리 설정이 `models` 폴더에 다운로드됩니다. 고정된 리비전과 SHA-256으로 세 파일을 검증하며, 이미 정상인 파일은 다시 다운로드하지 않습니다. 손상되거나 누락된 파일은 같은 명령으로 복원할 수 있습니다. 원격 Python 코드는 실행하지 않습니다.

- 모델: [onnx-community/house-plant-image-detection-ONNX](https://huggingface.co/onnx-community/house-plant-image-detection-ONNX).
- 원본: [dima806/house-plant-image-detection](https://huggingface.co/dima806/house-plant-image-detection).
- 형식: ViT INT8 ONNX, `CPUExecutionProvider`, 실내 식물 47개 범주.
- 리비전: `24d519d5ce1dd1a44b159b4e1bef012d01f30b95`.
- 모델 SHA-256: `d746a150317b670ed308c243b4aba46f1c0e69c5d1da68e7713b8aca72097c0b`.
- 모델 카드의 라이선스: Apache-2.0. 모델 사용·재배포 조건은 출처를 확인하세요.

모델은 Git에 포함되지 않으므로 저장소를 새로 받은 사람은 이 준비 명령을 실행해야 합니다.

## 실행 방법

```powershell
python run.py
```

모델 로드와 `Uvicorn running on http://127.0.0.1:8000` 메시지를 확인한 뒤 브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000)을 엽니다.

1. **이미지 선택**을 눌러 본인의 식물 사진을 선택하거나 업로드 영역에 끌어 놓습니다.
2. 미리보기를 확인하고 **식물 후보 분석하기**를 누릅니다.
3. 상위 후보 3개, 모델 상대 점수, 분석 시간과 추정 안내를 확인합니다.

JPG·PNG·WebP, 파일당 최대 10MiB, 2,000만 화소 이하의 정지 이미지를 지원합니다. 종료는 서버를 실행한 PowerShell에서 `Ctrl+C`를 누릅니다. 기본 실행에는 계정·API 키·환경변수 설정이 필요하지 않습니다.

포트 8000이 이미 사용 중이면 기존 프로그램을 종료하지 말고 다른 포트를 선택합니다.

```powershell
python run.py --port 8001
```

이 경우 [http://127.0.0.1:8001](http://127.0.0.1:8001)에 접속하세요. 서버는 `127.0.0.1`에만 연결되며 다른 기기에 공개되지 않습니다.

## 오류 해결

- **의존성 누락:** 프로젝트 폴더에서 설치 명령을 실행했는지 확인하세요. 패키지 설치와 실행에는 같은 `python`을 사용해야 합니다.
- **모델 준비 필요 / 503:** 서버 로그를 확인하고 `python prepare_model.py`를 실행한 뒤 서버를 다시 시작하세요.
- **다운로드 실패:** 오류에 표시된 네트워크·DNS·인증서 원인을 확인하고 정상 연결에서 다시 시도하세요. 인증서 검증이나 보안 설정을 끄지 마세요.
- **이미지 오류 / 400:** 손상되지 않은 지원 형식의 정지 이미지를 선택하세요. 서버가 실제 파일 내용을 디코딩하므로 확장자 변경만으로 지원 형식이 되지 않습니다.
- **크기 초과 / 413:** 이미지 파일 크기나 해상도를 줄이세요.
- **분석 중 / 429:** 다른 요청이 끝난 뒤 다시 시도하세요.
- **서버 연결 실패:** 서버가 실행 중인지와 브라우저 주소의 포트를 확인하세요.

## 한계와 검증 상태

몬스테라·알로에·난초 등 모델이 학습한 47개 범주만 비교합니다. 모든 식물 종을 식별하거나 비식물 사진을 감지하는 도구는 아닙니다. 지원하지 않는 식물이나 식물이 아닌 사진도 후보가 나올 수 있습니다. 한글 이름은 참고용이며 원래 모델 라벨을 함께 표시합니다. 최대 상대 점수가 60% 미만이면 불확실 안내를 추가하지만 이 기준도 정확도 보장은 아닙니다. 식용·독성 판단에는 사용하지 마세요.

실제 JPG·PNG·WebP 분류, 빈 파일·손상 파일·크기 초과·화소 제한 등 **API 검증 15개를 통과**했습니다. 실제 Chrome에서는 초기 화면과 모델 준비 상태까지 확인했습니다. **브라우저의 파일 선택·미리보기·분석 결과 표시까지 이어지는 전체 흐름은 아직 검증을 완료하지 못했습니다.** API 성공을 브라우저 검증 성공으로 간주하지 않습니다.

## Docker 실행 및 자동 게시

Docker의 Linux 컨테이너 모드에서 아래 명령을 실행합니다. 빌드 대상은 `linux/amd64`이며, Python 3.14.8과 기존 `requirements.txt`를 사용합니다.

```powershell
docker build --platform linux/amd64 -t greendex:local .
docker run --rm -p 127.0.0.1:8000:8000 greendex:local
```

[http://127.0.0.1:8000](http://127.0.0.1:8000)에서 앱을 사용합니다. 이미지는 빌드 중 공개 모델을 내려받아 SHA-256을 확인하고, 앱과 동일한 로더로 CPU 추론을 한 번 실행합니다. 다운로드·설치·추론 중 하나라도 실패하면 빌드가 실패합니다. 모델을 이미지에 포함하므로 실행할 때 모델을 별도로 준비하거나 인터넷에 연결할 필요가 없습니다.

GitHub Actions를 사용하려면 Docker Hub에 `greendex` 저장소를 준비하고, GitHub 저장소의 **Settings → Secrets and variables → Actions → Repository secrets**에 다음 값을 등록합니다.

| Secret | 값 |
| --- | --- |
| `DOCKERHUB_USERNAME` | Docker Hub 사용자 이름 |
| `DOCKERHUB_TOKEN` | 해당 저장소에 push할 수 있는 Docker Hub 액세스 토큰 |

`main`으로 향하는 PR은 이미지 빌드와 HTTP 준비 상태를 확인합니다. `main`에 push하면 같은 검사를 통과한 이미지를 `<Docker Hub 사용자 이름>/greendex:latest`와 커밋 SHA 태그로 게시합니다. 토큰은 게시 단계에서만 사용됩니다. 첫 push 후 GitHub **Actions → Docker CI**에서 빌드 및 게시 결과를 확인할 수 있습니다.

## 저장소 구성

```text
app.py             FastAPI 경로, 업로드 제한, 오류 처리
classifier.py      CPU 모델 로드, 이미지 전처리, 추론
prepare_model.py   모델 다운로드 및 무결성 검증
run.py             프로젝트 패키지 로드와 로컬 서버 실행
requirements.txt   버전이 고정된 실행 의존성
static/            HTML, CSS, JavaScript, 앱 아이콘
Dockerfile         Linux CPU 이미지 빌드 및 모델 추론 검증
.dockerignore      Docker 빌드 컨텍스트의 파일 허용 목록
.github/workflows/ci.yml   GitHub Actions 빌드 및 Docker Hub 게시
README.md          설치 및 실행 안내
.gitignore         공유할 파일의 허용 목록
```

`.gitignore`는 위의 검토된 실행 파일만 허용합니다. `.packages`, `models`, 실행 중 생성되는 파일, 캐시, 로그, 업로드, 테스트 이미지·검증 기록, 인증정보·개인 파일은 공유 대상에서 제외됩니다. 새 소스 파일을 추가할 때에는 내용을 검토한 뒤 `.gitignore`의 허용 목록에도 추가해야 합니다. 이미 Git에서 추적 중인 파일에는 ignore 규칙이 적용되지 않으며, 강제 추가(`git add -f`)도 사용하지 마세요.
