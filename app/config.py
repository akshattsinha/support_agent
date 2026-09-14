from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    ollama_base_url:str="http://localhost:11434"
    ollama_model:str="qwen3.5:4b"
    database_url:str="sqlite:///./support_agent.db"
    knowledge_base_dir:str="./knowledge_base"
    top_k:int=4
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")
settings=Settings()
