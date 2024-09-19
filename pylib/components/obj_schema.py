# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.obj_schema
'''
Common components for object schema (basically Pydantic)
'''
# from pathlib import Path

from pydantic import ValidationError


def validate_json(data, pyd_mod):
    '''
    Validate a Python object structure (presumably deserialized fromJSON) & convert to a provided Pydantic model
    '''
    try:
        validated_data = pyd_mod(**data)
        return validated_data
    except ValidationError as e:
        raise e
