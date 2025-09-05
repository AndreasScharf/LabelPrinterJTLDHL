from dotenv import load_dotenv
from window import App

def main():
    print('Main execution')
    load_dotenv()  # Load environment variables from .env file
    App().mainloop()



if __name__ == '__main__': 
    main()