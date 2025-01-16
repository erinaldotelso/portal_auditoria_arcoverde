from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import os

# Escopo necessário para acessar o Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_google_drive():
    """Autentica o usuário e cria um serviço do Google Drive."""
    creds = None
    # Verifica se já existe um token salvo
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # Se não houver token ou ele for inválido, gere um novo
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secret_421810971756-tlht5pltku8kd36auc1oddtp6g0sttkl.apps.googleusercontent.com.json', SCOPES
        )
        # Força o uso de 127.0.0.1 para o redirecionamento
        creds = flow.run_local_server(
            host='127.0.0.1', port=5000
        )
        # Salva o token para reutilização futura
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Conecta ao Google Drive usando as credenciais
    service = build('drive', 'v3', credentials=creds)
    return service

if __name__ == '__main__':
    service = authenticate_google_drive()
    print("Autenticação bem-sucedida!")
