# VS Code 디버깅 설정 가이드

이 프로젝트는 Poetry를 사용한 마이크로서비스 아키텍처로 구성되어 있으며, VS Code에서 Poetry 환경으로 디버깅할 수 있도록 설정되어 있습니다.

## 🚀 Poetry 디버깅 설정

### Poetry 통합 디버깅

- **설명**: Poetry 가상환경을 직접 사용하여 서비스를 실행
- **장점**:
  - 의존성 관리가 완벽하고, Poetry 설정과 완전히 동기화
  - 자동으로 Poetry 의존성 설치 후 실행
  - 개발 환경에 최적화된 설정
- **사용법**:
  - `F5` 키를 누르거나 디버그 패널에서 "Debug [Service]" 선택
  - 자동으로 Poetry 의존성 설치 후 실행

## 🛠️ 사용 가능한 작업 (Tasks)

### Poetry 관련 작업

1. **Poetry Install [Service]**: 개별 서비스의 의존성 설치
2. **Poetry Install All Services**: 모든 서비스의 의존성 병렬 설치
3. **Poetry Update All Services**: 모든 서비스의 의존성 업데이트
4. **Poetry Build All Services**: 모든 서비스를 빌드
5. **Poetry Export Requirements**: requirements.txt 파일 생성

### 작업 실행 방법

- `Ctrl+Shift+P` → "Tasks: Run Task" → 원하는 작업 선택

## 🎯 복합 실행 (Compounds)

여러 서비스를 동시에 실행할 수 있는 설정:

1. **Start All Services**: 모든 서비스를 Poetry 환경으로 실행

## 📁 서비스별 포트

- **API Gateway**: 33330
- **Board Service**: 33333
- **User Service**: 33334
- **Comment Service**: 33335

## 🔧 환경 설정

- **환경 파일**: 프로젝트 루트의 `.env` 파일 사용
- **Python 경로**: 각 서비스별로 자동 설정
- **가상환경**: 각 서비스의 `.venv` 디렉토리 사용

## 💡 권장 사용법

### 개발 시

1. **개발 중**: "Debug [Service]" 사용
2. **전체 테스트**: "Start All Services" 사용
3. **의존성 업데이트**: "Poetry Update All Services" 실행

## 🐛 문제 해결

### Poetry 가상환경이 없는 경우

1. 각 서비스 디렉토리에서 `poetry install` 실행
2. 또는 VS Code에서 "Poetry Install All Services" 작업 실행

### 의존성 충돌이 있는 경우

1. "Poetry Update All Services" 실행
2. 필요시 `poetry.lock` 파일 삭제 후 재설치

### 포트 충돌이 있는 경우

- `launch.json`에서 각 서비스의 포트 번호를 변경
- 또는 실행 중인 프로세스를 종료

## 📝 추가 정보

- 모든 설정은 `.vscode/launch.json`과 `.vscode/tasks.json`에 저장
- Poetry 설정은 각 서비스의 `pyproject.toml`에서 관리
- 환경 변수는 프로젝트 루트의 `.env` 파일에서 관리
- 운영서버는 Docker로 배포되므로 로컬 개발 환경과 분리됨
