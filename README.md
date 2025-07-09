# TrafficDetectorBackend

Обновление от 10.07.2025: <br/>
Новая команда для докера которая поднимает все микросервисы:<br/>
`docker compose up --build -d`
<br/>

Команда для поднятия микросервисов(кроме ИИ) в docker:<br/>
`docker compose up --build auth-service video-service statistics-service -d`
<br/><br/>
документация auth service: `http:localhost:8001/swagger/` <br/>
документация video service: `http:localhost:8002/swagger/` <br/>
документация ml service (ИИ): `http:localhost:8003/swagger/` <br/>
проверка ml service (ИИ): `http:localhost:8003/health/` <br/>
документация statistics service: `http:localhost:8004/swagger/` <br/>
