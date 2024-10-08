# SPDX-FileCopyrightText: 2024-present Oori Data <info@oori.dev>
#
# SPDX-License-Identifier: Apache-2.0
# arkestra.components.prompt.composite
'''
Common components for prompt assembly & handling
'''
from dataclasses import dataclass


@dataclass
class base_64_image:
    '''Base64 encoded image data'''
    # TODO: Override for full MIME types
    type: str
    filename: str
    data: str | bytes


def composite_prompt_content(text, base64_images=None):
    '''
    Support OpenAI-style prompting with included attachments
    Note: Image attachment types only, for now
    '''
    base64_images = base64_images or []
    if not base64_images:
        # Degenerate to scalar prompt
        return text
    content = [
            {
                'type': 'text',
                'text': text
            }
    ]
    for img in base64_images:
        content.append({
                'type': 'image_url',
                'image_url': {
                    'url': f'data:image/{img.type};base64,{img.data}'
                }
            })
    return content
