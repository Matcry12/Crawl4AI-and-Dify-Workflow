# RAG Quality Optimization - Quick Start Guide

**TL;DR**: Systematic approach to improve RAG quality from 60% → 90% Recall@5

---

## The Problem

Your current system is **good (82.1/100)**, but has room for improvement:
- ❌ No evaluation metrics (flying blind)
- ❌ Vector-only search (misses exact matches)
- ❌ No reranking (imprecise retrieval)
- ❌ Basic chunking (breaks semantic boundaries)

---

## The Solution: 4-Phase Roadmap

### Phase 1: Measurement (Week 1) ⭐⭐⭐
**Why**: Can't improve without metrics
**What**: Create 70 test queries + evaluation framework
**Expected**: Baseline metrics established

### Phase 2: Quick Wins (Week 2-3) ⭐⭐⭐
**Why**: High ROI improvements
**What**: Hybrid search + Query expansion + Two-stage retrieval
**Expected**: +20-40% improvement in Recall@5

### Phase 3: Advanced (Week 4-6) ⭐⭐
**Why**: Further optimization
**What**: Semantic chunking + Deduplication + Quality scoring
**Expected**: +10-20% additional improvement

### Phase 4: Production (Week 7-8) ⭐
**Why**: Continuous improvement
**What**: A/B testing + Monitoring + Automation
**Expected**: Sustained quality over time

---

## Top 5 Improvements by ROI

### 1. Evaluation Framework (Week 1)
**Impact**: Essential foundation
**Effort**: 1 week
**ROI**: ∞ (enables all other improvements)

```bash
# Create test queries
python create_test_queries.py --count 70

# Run evaluation
python evaluate_rag.py --output baseline_metrics.json
```

### 2. Hybrid Search (Week 2)
**Impact**: +15-30% Recall@5
**Effort**: 2 days
**ROI**: Very High

```sql
-- Add PostgreSQL FTS
ALTER TABLE chunks ADD COLUMN content_tsv tsvector;
CREATE INDEX idx_chunks_fts ON chunks USING GIN(content_tsv);
```

```python
# Combine vector + keyword
results = hybrid_search(query, alpha=0.7)  # 70% semantic, 30% keyword
```

### 3. Two-Stage Retrieval (Week 2-3)
**Impact**: +20-40% precision
**Effort**: 3 days
**ROI**: Very High

```python
# Stage 1: Fast retrieval (top 20)
candidates = vector_search(query, top_k=20)

# Stage 2: Precise reranking (top 5)
results = llm_rerank(candidates, final_k=5)
```

### 4. Semantic Chunking (Week 4)
**Impact**: +10-20% relevance
**Effort**: 3 days
**ROI**: Medium-High

```python
# Chunk by meaning, not size
chunker = SemanticChunker(threshold=0.7)
chunks = chunker.chunk(document)
```

### 5. Query Expansion (Week 2)
**Impact**: +10-15% recall
**Effort**: 1 day
**ROI**: High

```python
# Generate query variants
variants = expand_query("How to stake EOS?")
# -> ["How to stake EOS?", "Staking EOS tokens", "EOS resource allocation"]

# Search with all variants
results = search_multi_query(variants)
```

---

## Key Metrics to Track

| Metric | What it Measures | Current | Target |
|--------|------------------|---------|--------|
| **Recall@5** | % relevant docs in top 5 | ~60% | 90%+ |
| **MRR** | Position of 1st relevant | ~0.45 | 0.75+ |
| **Faithfulness** | Answer grounded in context | ~82% | 87%+ |
| **Relevance** | Answer addresses query | ~75% | 88%+ |

---

## Implementation Priority

**Week 1**: Measurement
```bash
1. Create test_queries.json (70 queries)
2. Implement RAGEvaluator class
3. Run baseline evaluation
4. Document weak areas
```

**Week 2**: Hybrid Search + Query Expansion
```bash
1. Add PostgreSQL FTS (2 hours)
2. Implement hybrid_search() (4 hours)
3. Implement query_expansion() (2 hours)
4. Evaluate improvements (2 hours)
```

**Week 3**: Two-Stage Retrieval
```bash
1. Implement TwoStageRetriever (4 hours)
2. Add LLM reranking (2 hours)
3. Optimize batch reranking (2 hours)
4. Evaluate improvements (2 hours)
```

**Week 4-6**: Advanced Optimizations
```bash
1. Semantic chunking (3 days)
2. Deduplication (1 day)
3. Quality scoring (2 days)
4. Evaluate improvements (1 day)
```

**Week 7-8**: Production Hardening
```bash
1. A/B testing framework (2 days)
2. Production monitoring (2 days)
3. Synthetic query generation (1 day)
4. Performance optimization (2 days)
```

---

## Quick Start Commands

### 1. Establish Baseline
```bash
# Install dependencies
pip install sentence-transformers scikit-learn tqdm

# Create test queries
python scripts/create_test_queries.py --manual 20 --synthetic 50

# Run evaluation
python scripts/evaluate_baseline.py
```

### 2. Add Hybrid Search
```bash
# Update database
psql -U postgres -d crawl4ai -f sql/add_fts.sql

# Test hybrid search
python scripts/test_hybrid_search.py --alpha 0.7
```

### 3. Compare Results
```bash
# Run A/B comparison
python scripts/compare_variants.py \
  --baseline vector_only \
  --variant hybrid_search \
  --test-queries test_queries.json
```

---

## Expected Timeline & Results

| Phase | Duration | Recall@5 | MRR | Effort |
|-------|----------|----------|-----|--------|
| Baseline | - | 60% | 0.45 | - |
| Phase 1 | 1 week | 60% | 0.45 | Setup |
| Phase 2 | 2 weeks | **80%** | **0.60** | ⭐⭐⭐ |
| Phase 3 | 3 weeks | **88%** | **0.70** | ⭐⭐ |
| Phase 4 | 2 weeks | **90%+** | **0.75+** | ⭐ |

**Total Timeline**: 8 weeks
**Total Improvement**: +50% Recall@5 (60% → 90%)

---

## Files to Create

### Core Implementation Files
```
scripts/
├── create_test_queries.py          # Generate test dataset
├── rag_evaluator.py                # Evaluation framework
├── hybrid_retrieval.py             # Hybrid search
├── two_stage_retrieval.py          # Retrieval + reranking
├── query_optimizer.py              # Query expansion/classification
├── semantic_chunker.py             # Semantic chunking
├── hierarchical_chunker.py         # Multi-level chunking
├── deduplicator.py                 # Remove duplicates
├── quality_scorer.py               # Document quality metrics
├── continuous_evaluator.py         # A/B testing
└── production_monitor.py           # Live monitoring
```

### Configuration Files
```
config/
├── test_queries.json               # Test dataset
├── evaluation_config.yaml          # Evaluation settings
└── retrieval_config.yaml           # Retrieval parameters
```

### SQL Files
```
sql/
├── add_fts.sql                     # Full-text search setup
├── add_quality_metrics.sql         # Quality scoring columns
└── create_materialized_views.sql   # Performance views
```

---

## Success Criteria

### Phase 1 ✅
- [ ] 70+ test queries created
- [ ] Evaluation runs in < 10 minutes
- [ ] Baseline metrics documented
- [ ] Top 3 weaknesses identified

### Phase 2 ✅
- [ ] Hybrid search implemented
- [ ] Recall@5 improved by 20%+
- [ ] Query expansion working
- [ ] Two-stage retrieval tested

### Phase 3 ✅
- [ ] Semantic chunking deployed
- [ ] 5-10% duplicates removed
- [ ] Quality scores calculated
- [ ] Recall@5 reaches 85%+

### Phase 4 ✅
- [ ] A/B testing automated
- [ ] Daily quality reports generated
- [ ] Production monitoring active
- [ ] Response time < 3s p95

---

## Common Pitfalls to Avoid

### ❌ Don't:
1. **Skip evaluation** - You'll waste time on changes that don't help
2. **Optimize too early** - Measure first, optimize second
3. **Change multiple things** - Can't tell what helped
4. **Ignore baselines** - Need comparison point
5. **Focus on accuracy only** - Speed and cost matter too

### ✅ Do:
1. **Start with metrics** - Evaluation framework first
2. **A/B test changes** - Compare scientifically
3. **Document everything** - Track what works
4. **Iterate quickly** - Small improvements compound
5. **Monitor production** - Catch regressions early

---

## Cost Considerations

### Gemini API Costs (Estimated)

**Current**:
- Embeddings: ~$0.001 per 1000 tokens
- LLM calls: ~$0.0001 per 1000 tokens (flash-lite)
- Monthly: ~$50-100 for moderate usage

**After Optimization**:
- Additional LLM reranking: +$20-30/month
- Query expansion: +$10-15/month
- Evaluation runs: +$5-10/month
- **Total**: ~$85-155/month

**Optimization Tips**:
- Batch rerank calls (10 docs per call)
- Cache query expansions
- Use flash-lite for non-critical tasks
- Implement request debouncing

---

## Questions?

Refer to the full guide: `RAG_QUALITY_OPTIMIZATION_GUIDE.md` (16,000+ words)

**Key Sections**:
- Detailed code examples
- Research paper citations
- Advanced techniques
- Production best practices

---

## Next Steps

**Today**:
1. ✅ Read this guide
2. ✅ Review `RAG_QUALITY_OPTIMIZATION_GUIDE.md`
3. ✅ Decide on timeline (8 weeks recommended)

**This Week**:
1. ✅ Create test_queries.json (20 manual + 50 synthetic)
2. ✅ Implement RAGEvaluator class
3. ✅ Run baseline evaluation
4. ✅ Share results with team

**Next Week**:
1. ✅ Add PostgreSQL FTS
2. ✅ Implement hybrid search
3. ✅ Run A/B comparison
4. ✅ Document improvements

---

**Let's build a world-class RAG system!** 🚀

For questions or clarifications, refer to research papers cited in the full guide.
