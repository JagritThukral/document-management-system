from openai import AsyncOpenAI


class EmbeddingsService:
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai_client = openai_client

    async def create_embedding(self, input_text: str):
        response = await self.openai_client.embeddings.create(
            input=input_text,
            model="text-embedding-3-small"
        )

        embedding = response.data[0].embedding

        print(
            f"[EmbeddingService] text = {input_text} embedding_dimensions = {len(embedding)}")
        # Print first 5 values for brevity
        print(f"[EmbeddingService] embedding = {embedding[:5]}...")
        return embedding

    async def create_embeddings(self, input_texts: list[str]):
        if not input_texts:
            return []

        response = await self.openai_client.embeddings.create(
            input=input_texts,
            model="text-embedding-3-small"
        )

        embeddings = [item.embedding for item in response.data]

        print(
            f"[EmbeddingService] batch_size = {len(input_texts)} embedding_dimensions = {len(embeddings[0])}")
        return embeddings
