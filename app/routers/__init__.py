from typing import Annotated
from fastapi import Query


MaxPerPageType = Annotated[int, Query(gt=0, le=9223372036854775807)]
PageType = Annotated[int, Query(gt=0, le=9223372036854775807)]

