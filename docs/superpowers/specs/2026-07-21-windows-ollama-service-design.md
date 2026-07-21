# Windows Ollama 자동 시작 서비스 설계

## 목표

Windows AI PC `100.118.130.61`에서 Ollama를 사용자 로그인 없이 부팅 시 자동으로 시작하고, 프로세스 장애 시 자동 재시작한다.

## 구성

- 기존 Ollama 실행 파일 `C:\Users\hwanj\AppData\Local\Programs\Ollama\ollama.exe`를 사용한다.
- NSSM으로 `ollama serve`를 Windows 서비스 `Ollama`로 등록한다.
- 서비스 시작 유형은 `Automatic (Delayed Start)`로 설정해 네트워크와 GPU 드라이버 초기화 후 실행한다.
- 서비스 실패 시 5초 후 재시작하도록 Windows 서비스 복구 정책을 설정한다.
- 서비스는 부팅 전 로그인을 요구하지 않도록 `LocalSystem` 계정으로 실행한다.
- 기존 모델을 그대로 사용하도록 `OLLAMA_MODELS=C:\Users\hwanj\.ollama\models`를 서비스 환경에 명시한다.
- 기존 사용자 환경변수와 동일하게 `OLLAMA_HOST=100.118.130.61:11434`를 서비스 환경에 명시한다.
- TCP 11434 인바운드 방화벽 규칙은 백엔드 연결에 필요한 범위로 유지하거나 생성한다.

## 검증

1. 서비스 상태와 시작 유형을 확인한다.
2. AI PC 로컬에서 `/api/tags` 응답을 확인한다.
3. 현재 작업 PC에서 `100.118.130.61:11434/api/tags` 응답을 확인한다.
4. 서비스를 강제 종료한 뒤 자동 복구되는지 확인한다.

## 롤백

서비스를 중지하고 NSSM 서비스 등록을 제거한다. Ollama 실행 파일, 모델, 사용자 환경변수는 삭제하지 않는다.
