class BM25:
    """BM25算法"""
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.avdl = sum(len(doc) for doc in corpus) / len(corpus)
