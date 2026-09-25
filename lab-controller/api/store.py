import asyncio
import json
import logging


logger = logging.getLogger("lab-controller")


class PersistentStore:


    ALLOWED_TABLES = ("lab.incidents", "lab.postmortems", "lab.toil_tasks")

    def __init__(self, pool, table: str, model):
        if table not in self.ALLOWED_TABLES:
            raise ValueError(f"Table non autorisee: {table}")
        self.pool = pool
        self.table = table
        self.model = model
        self._cache = {}
        self._writes = set()

    async def load(self):
        rows = await self.pool.fetch(
            "SELECT id, content FROM %s" % self.table)
        self._cache = {}
        for row in rows:
            try:
                self._cache[row["id"]] = self.model(**json.loads(row["content"]))
            except Exception as exc:
                logger.warning("Objet %s illisible dans %s: %s", row["id"], self.table, exc)
        logger.info("%s: %d objet(s) charge(s)", self.table, len(self._cache))
        return self

    def _persist(self, key: str, value):
        payload = value.model_dump_json() if hasattr(value, "model_dump_json") else json.dumps(value)

        async def _write():
            try:
                await self.pool.execute(
                    "INSERT INTO %s (id, content) VALUES ($1, $2::jsonb) "
                    "ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content" % self.table,
                    key, payload)
            except Exception as exc:
                logger.error("Echec d'ecriture %s/%s: %s", self.table, key, exc)

        task = asyncio.create_task(_write())
        self._writes.add(task)
        task.add_done_callback(self._writes.discard)


    def __setitem__(self, key, value):
        self._cache[key] = value
        self._persist(key, value)

    def __getitem__(self, key):
        return self._cache[key]

    def __contains__(self, key):
        return key in self._cache

    def __len__(self):
        return len(self._cache)

    def __iter__(self):
        return iter(self._cache)

    def get(self, key, default=None):
        return self._cache.get(key, default)

    def values(self):
        return self._cache.values()

    def keys(self):
        return self._cache.keys()

    def items(self):
        return self._cache.items()
