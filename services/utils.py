
def convert_chat_completion_response_to_completion_response(chat_completion):
    choices = []
    for ch in chat_completion.choices:
        text_offset, offset, token_logprobs, tokens, top_logprobs = [], 0, [], [], []
        for cnt in ch.logprobs.content:
            text_offset.append(offset)
            offset += len(cnt.token)
            token_logprobs.append(cnt.logprob)
            tokens.append(cnt.token)
            top_logprobs.append({x.token: x.logprob for x in cnt.top_logprobs})
        choice = {
            "index": ch.index,
            "text": ch.message.content,
            "logprobs": {
                "text_offset": text_offset,
                "token_logprobs": token_logprobs,
                "tokens": tokens,
                "top_logprobs": top_logprobs
            },
            
        }
        choices.append(choice)
    chat_completion.choices = choices

    completion = chat_completion.__dict__
    return completion