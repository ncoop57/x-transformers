import tqdm
import torch
import torch.optim as optim
from x_transformers import XTransformer

# constants

NUM_BATCHES = int(1e5)
BATCH_SIZE = 32
LEARNING_RATE = 3e-4
GENERATE_EVERY  = 100
NUM_TOKENS = 16 + 2
NUM_SECONDARY_TOKENS = 16 + 2
ENC_SEQ_LEN = 32
DEC_SEQ_LEN = 64 + 1

# helpers

def cycle():
    while True:
        prefix = torch.ones((BATCH_SIZE, 1)).long().cuda()
        src = torch.randint(2, NUM_TOKENS, (BATCH_SIZE, ENC_SEQ_LEN)).long().cuda()
        tgt = torch.cat((prefix, src, src), 1)
        sec_tgt = torch.cat((prefix, src, src), 1)
        src_mask = torch.ones(BATCH_SIZE, src.shape[1]).bool().cuda()
        tgt_mask = torch.ones(BATCH_SIZE, tgt.shape[1]).bool().cuda()
        yield (src, tgt, sec_tgt, src_mask, tgt_mask)

# instantiate model

model = XTransformer(
    dim = 512,
    tie_token_embeds = True,
    return_tgt_loss = True,
    enc_num_tokens=NUM_TOKENS,
    enc_depth = 3,
    enc_heads = 8,
    enc_max_seq_len = ENC_SEQ_LEN,
    dec_num_tokens = NUM_TOKENS,
    dec_num_secondary_tokens = NUM_SECONDARY_TOKENS,
    dec_depth = 3,
    dec_heads = 8,
    dec_max_seq_len = DEC_SEQ_LEN
).cuda()

# optimizer

optim = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

# training

for i in tqdm.tqdm(range(NUM_BATCHES), mininterval=10., desc='training'):
    model.train()

    src, tgt, sec_tgt, src_mask, tgt_mask = next(cycle())

    loss = model(src, tgt, sec_tgt=sec_tgt, src_mask=src_mask, tgt_mask=tgt_mask)
    loss.backward()
    print(f'{i}: {loss.item()}')

    optim.step()
    optim.zero_grad()

    if i != 0 and i % GENERATE_EVERY == 0:
        model.eval()
        src, _, _, src_mask, _ = next(cycle())
        src, src_mask = src[:1], src_mask[:1]
        start_tokens = (torch.ones((1, 1)) * 1).long().cuda()

        sample = model.generate(src, start_tokens, ENC_SEQ_LEN, src_mask=src_mask)
        incorrects = (src != sample).abs().sum()

        print(f"input:  ", src)
        print(f"predicted output:  ", sample)
        print(f"incorrects: {incorrects}")
