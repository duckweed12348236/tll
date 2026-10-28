from typing import Any

import tortoise
from tortoise.fields import ManyToManyRelation


class Model(tortoise.Model):
    excluded_fields = {"_partial", "_saved_in_db", "_custom_generated_pk", "_await_when_save"}

    def serialize(self) -> dict[str, Any]:
        pairs = {}
        excluded_fields = self.excluded_fields
        for key, value in self.__dict__.items():
            if key in excluded_fields:
                continue
            if key.startswith("_"):
                key = key[1:]

            if isinstance(value, Model):
                pairs[key] = value.serialize()
            elif ((isinstance(value, list) and len(value) > 0 and isinstance(value[0], Model)) or
                  isinstance(value, ManyToManyRelation)):
                pairs[key] = [x.serialize() for x in value]
            else:
                pairs[key] = value
        return pairs
