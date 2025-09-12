from dotenv import load_dotenv
from window import App

from utils import asset_path

def main():
    print('Main execution')
    # Load .env file from the same folder as the exe
    dotenv_path = asset_path(".env")
    load_dotenv(dotenv_path)

    print(f"""Loaded environment from {dotenv_path}:""")
    App().mainloop()



if __name__ == '__main__': 
    main()