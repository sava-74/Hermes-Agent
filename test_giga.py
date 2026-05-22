from gigachat import GigaChat
from gigachat.models import Chat, ChatCompletionRequestMessage, Role

# Ваш Base64-токен
CREDENTIALS = "ZjYxMTUyZDUtNTVjYi00NzdlLWEyOTktYTVlMzM5ZDIwZTI4OmQ0ZmNhZWU3LTgwNDItNGNhNi04YmI0LWFiMjFkOWY5ZTM0YQ=="

try:
    # Создаём клиента
    with GigaChat(credentials=CREDENTIALS, scope="GIGACHAT_API_PERS", verify_ssl_certs=False) as giga:
        
        # Создаём сообщения
        messages = [
            ChatCompletionRequestMessage(
                role=Role.USER,
                content="Расскажи короткую шутку про Python"
            )
        ]
        
        # Создаём объект запроса
        chat = Chat(messages=messages)
        
        # Отправляем
        response = giga.chat(chat=chat)
        
        print("✅ Ответ от GigaChat:")
        print(response.choices[0].message.content)

except Exception as e:
    print("❌ Ошибка:", e)