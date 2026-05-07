from pydantic import BaseModel


class Schema(BaseModel):
    class Config:
        from_attributes = True
