link https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python?tabs=asgi%2Capplication-level&pivots=python-mode-configuration#python-version-and-package-management  
the problem with functions:  
add to requirements.txt  
pip install -r requirements.txt  
may be more steps here: https://stackoverflow.com/questions/75942313/azure-functions-with-vs-code-and-python-modulenotfounderror-no-module-named-a  


python -m venv .venv  

source .venv/bin/activate  

func init LocalFunctionProj --python  

cd LocalFunctionProj  

func new --name HttpExample --template "HTTP trigger" --authlevel "anonymous"  

func start  

ps aux  

kill -9 pid  

func azure functionapp publish <APP_NAME>  

link https://learn.microsoft.com/en-us/azure/azure-functions/create-first-function-cli-python?pivots=python-mode-configuration&tabs=bash%2Cazure-cli  

