from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """요청/응답 JSON은 camelCase, 파이썬 속성은 snake_case."""

    # protected_namespaces=(): modelVersion 같은 필드가 pydantic의 model_ 예약 접두사와 부딪히는 것을 막는다.
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, protected_namespaces=())
