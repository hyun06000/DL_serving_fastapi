# 지속 가능한 AI Serving
이 저장소는 MLOps에 관한 문서들과 태크들을 모아놓은 이 [저장소](https://github.com/State-of-The-MLOps/MLOps)를 클론 코딩하며 하나씩 익혀보는 기록을 남긴 곳입니다.  
좋은 자료를 제공해 주신 contributors 분들께 감사드립니다.  
자세한 해석과 따라가는 과정은 저의 [블로그](https://davi06000.tistory.com/128) 를 통해서 확인할 수 있습니다.  
모든 작업은 로컬의 windows 에서 ubuntu server에 접속하여 원격으로 진행되고 있습니다.  
최종적으로는 Continuous Training 을 구현하는 것이 이 저장소의 목표입니다.  

## 진행상황
- fastapi를 이용한 간단한 서버 구현 및 도커파일로 작성하여 빌드  
![image](https://user-images.githubusercontent.com/35767146/144759692-95d98d98-5f3a-4feb-b50a-233cf6ebdbab.png)  
- PostgreSQL 을 이용한 db 구축 및 fastapi 서버와 연동
![image](https://user-images.githubusercontent.com/35767146/144759764-8d0396b2-4e74-45d6-be3d-68fc5f137df8.png)
- subprocess 를 이용한 NNI 서버 연동, 학습 모니터링
![image](https://user-images.githubusercontent.com/35767146/144759795-34d32411-af6d-4b49-94ae-f41e8d1b2daa.png)

## MAIN TODO
- MLflow, Kubeflow, bentoML 등 MLOps 툴을 이용한 DL 서버 분리
- 분리된 웹 서버, DB 서버, DL 서버를 각각 containerize 하여 통신
- 도커 컨테이너들을 Kubernetes를 통해 오케스트레이션

## SUB TODO
- BytesIO 를 이용한 원격 데이터 서버 관리
- MLflow 의 모델 레지스트리 원격으로 구현하여 팀원들과 협업
