@echo off
REM Altera para o diretório do seu projeto
cd "C:\Users\albuq\OneDrive\Documentos\BALANCETE-FINANCEIRO\01 - 1 mes"

REM Executa o Streamlit
REM Certifique-se de que 'python.exe' está no seu PATH ou use o caminho completo, ex: "C:\Program Files\Python313\python.exe"
python.exe -m streamlit run balancete.py --server.port 8501 --browser.gatherUsageStats false

pause