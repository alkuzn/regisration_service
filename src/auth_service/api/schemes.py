from pydantic import BaseModel, Field


class StartRegAnswer(BaseModel):
    success: bool = Field(examples=[True, False])
    sessionid: str = Field(examples=["lkajsdflakjfgl;sdkfj;sdlk"])


class FinishRegAnswer(BaseModel):
    success: bool = Field(examples=[True, False])


class StartLoginAnswer(BaseModel):
    success: bool = Field(examples=[True, False])
    sessionid: str = Field(examples=["lkajsdflakjfgl;sdkfj;sdlk"])


class FinishLoginAnswer(BaseModel):
    success: bool = Field(examples=[True, False])
    token: str = Field(examples=["lkajsdflakjfgl;sdkfj;sdlk"])


class Key(BaseModel):
    kid: str = Field(examples=["custom_key_id"])
    use: str = Field(examples=["sig", "enc"])
    alg: str = Field(examples=["RS256"])
    kty: str = Field(examples=["RSA"])
    n: str = Field(examples=["xsjWl1lmVS2rDB5k2CNo4uul4CH4BlRWn9R1V1UWYQ9hSn"])
    e: str = Field(examples=["AQABdf"])


class PublicKeyAnswer(BaseModel):
    keys: list[Key]
