#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Text Utils is a collection of helper functions and classes which are able to
deal with raw text file, and produce Bag-of-Words corpus and highly customized
vocabulary accordingly.
'''

from gensim import corpora, models
from gensim.matutils import corpus2dense, Dense2Corpus, corpus2csc
from collections import defaultdict
from nltk.util import ngrams
from six import iteritems
import numpy as np
import itertools
import string
import arrow
import nltk
import sys
import re

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

class Documents(object):
	'''
	Documents is a simple class for:
	1. preprocessing documents text in a memory-friendly way.
	2. outputting tokenized terms of each of the documents iteratively.

	It's mainly used to load the documents and help substantiate gensim's
	dictionary and corpus.

	Essentially, a documents is simply an iterable object, where each iteration
	step yields one document, then splits and formats their words by an unified
	and standard method.
	'''

	def __init__(self, iter_object, n=1, pad_right=False, pad_left=False, \
		         left_pad_symbol=None, right_pad_symbol=None, keep_sents=False, \
				 is_tokenzied=True):
		self.iter_object = iter_object
		self.counter     = 0
		self.n           = n
		self.pad_right   = pad_right
		self.pad_left    = pad_left
		self.keep_sents  = keep_sents
		self.left_pad_symbol  = left_pad_symbol
		self.right_pad_symbol = right_pad_symbol
		self.is_tokenzied     = is_tokenzied

	def __iter__(self):
		'''
        Iterate over the corpus, yielding one line (document) at a time.
        '''
		for line in self.iter_object:
			if self.counter > 0 and self.counter % 1000 == 0:
				print('[%s] [Documents] %s docs have been processed.' % (arrow.now(), self.counter), \
				      file=sys.stderr)
				# print >> sys.stderr, '[%s] [Documents] %s docs have been processed.' % \
				#          (arrow.now(), self.counter)
			try:
				if self.is_tokenzied:
					yield(self.string2tokens(line, N=self.n, \
                                             pad_right=self.pad_right, \
                                             pad_left=self.pad_left, \
					                         left_pad_symbol=self.left_pad_symbol, \
					                         right_pad_symbol=self.right_pad_symbol, \
									         keep_sents=self.keep_sents))
				else:
					yield(self.string2sents(line))
			# Yield empty token list if tokenization failed as UnicodeDecodeError was raised
			except Exception as e:
				print(line)
				print('[%s] [Documents] No. %s doc raise expection: %s.' % (arrow.now(), self.counter, e), \
				      file=sys.stderr)
				yield([])

			self.counter += 1

	@staticmethod
	def string2sents(text_string):
		'''
		Tokenize each of sentences in the text (one document as a line).

		It utilize nltk to tokenize the sentences in the text. And it will yield
		separated sentences string in a codument iteratively. E.g.
		doc = [ sent1_string, sent2_string, ... ]
		'''
		sents = []
		# For every sentences in each of the free text part
		for sent in nltk.tokenize.sent_tokenize(text_string.replace('\n','').strip()):
			sents.append(sent)
		return sents

	@staticmethod
	def string2tokens(text_string, N=1, pad_right=False, pad_left=False, \
		              left_pad_symbol=None, right_pad_symbol=None, \
				      keep_sents=False):
		'''
		Tokenize each of the words in the text (one document as a line).

		It utilizes nltk to tokenize the sentences and the words in the text.
		What needs to be noted is one document is consist of multiple remarks,
		which are delimited by '/1' within the text. It will yield tokenized
		documents iteratively. E.g.
		doc = [ token1, token2, token3, ... ]

		Also, parameters of ngrams module, like n, pad_right, pad_left,
		left_pad_symbol, and right_pad_symbol, are optional to input.

		Last but not least, you can set keep_sents True for keeping sentences
		structure in the form of a 2D array. E.g.
		doc = [ [ token1, token2, ... (sent1) ], [ (sent2) ], ... ]

		Note:
		If the yield documents are going to be used to generate vocabulary,
		'keep_sents' has to be set False, since the creation of dictionary only
		take 1D documents as input.
		'''
		ngram_tokens = []
		ngram_tokens_sents = []
		# For every sentences in each of the free text part
		for sent in nltk.tokenize.sent_tokenize(text_string.replace('\n','').strip()):
			# Tokenize a sentence by english word level of granularity
			tokens_in_sentence = [
				token
				for token in nltk.word_tokenize(sent.translate(str.maketrans('','',string.punctuation)).lower())
				if token not in nltk.corpus.stopwords.words('english')]
			# Calculate all the grams terms from unigram to N-grams
			ngram_tokens_in_sentence = []
			for n in range(1, N+1):
				# Calculate ngram of a tokenized sentence
				ith_gram_tokens_in_sentence = [
					'_'.join(ngram_tuple)
					for ngram_tuple in \
						list(ngrams(tokens_in_sentence, n, \
						            pad_right=pad_right, pad_left=pad_left, \
							        left_pad_symbol=left_pad_symbol, \
							        right_pad_symbol=right_pad_symbol)) ]
				# Append ngrams terms to the list
				ngram_tokens += ith_gram_tokens_in_sentence
				ngram_tokens_in_sentence += ith_gram_tokens_in_sentence
			# Collect all ngram tokens in the sentences to ngram_tokens_sents container
			ngram_tokens_sents.append(ngram_tokens_in_sentence)
		if keep_sents:
			return ngram_tokens_sents
		else:
			return ngram_tokens



def vocabulary(text_iter_obj, min_term_freq=1, \
               n=1, pad_right=False, pad_left=False, \
			   left_pad_symbol=None, right_pad_symbol=None):
	'''
	Create a new dictionary in accordance with indicated raw text.
	'''
	# Init document object by loading an iterable object (for reading text iteratively),
	# the iterable object could be a file handler, or standard input handler and so on
	docs = Documents(text_iter_obj, n=n, pad_right=pad_right, pad_left=pad_left,
					 left_pad_symbol=left_pad_symbol,
					 right_pad_symbol=right_pad_symbol)
	# Build dictionary based on the words appeared in documents
	dictionary = corpora.Dictionary(docs)
	# Remove non-character and low-frequency terms in the dictionary
	nonchar_ids = [ tokenid \
	                for token, tokenid in iteritems(dictionary.token2id) \
	                if not re.match('^[A-Za-z_]*$', token) ]
	lowfreq_ids = [ tokenid
	                for tokenid, docfreq in iteritems(dictionary.dfs) \
	                if docfreq <= min_term_freq ]
	dictionary.filter_tokens(lowfreq_ids + nonchar_ids)
	# Remove gaps in id sequence after some of the words being removed
	dictionary.compactify()
	return dictionary

def sub_vocabulary(dictionary, ngrams_list, by_key=False):
	'''
	Return a sub dictionary by indicating a ngrams list.
	'''
	print('[%s] [Sub Dict] Load existing dictionary: %s' % \
	      (arrow.now(), dictionary), file=sys.stderr)

	if by_key:
		remove_tokens = list(set(dictionary.keys()) - set(ngrams_list))
		remove_ids = [ token for token in remove_tokens]
	else:
		remove_tokens = list(set(dictionary.token2id.keys()) - set(ngrams_list))
		remove_ids = [ dictionary.token2id[token] for token in remove_tokens]
	print('[%s] [Sub Dict] %d tokens have been removed.' % \
	      (arrow.now(), len(remove_tokens)), file=sys.stderr)

	dictionary.filter_tokens(remove_ids)
	dictionary.compactify()
	print('[%s] [Sub Dict] New sub-dictionary has been created: %s' % \
	      (arrow.now(), dictionary), file=sys.stderr)

	return dictionary

def corpus(text_iter_obj, dictionary, \
           n=1, pad_right=False, pad_left=False, \
		   left_pad_symbol=None, right_pad_symbol=None):
	'''
	Create a new corpus in accordance with indicated raw text (one document each
	line) and dictionary.
	'''
	docs = Documents(text_iter_obj, n=n, pad_right=pad_right, pad_left=pad_left,
					 left_pad_symbol=left_pad_symbol,
					 right_pad_symbol=right_pad_symbol,
					 keep_sents=False, is_tokenzied=True)
	# Build corpus (numeralize the documents and only keep the terms that exist in dictionary)
	corpus = [ dictionary.doc2bow(doc) for doc in docs ]
	# # Calculate tfidf matrix
	# tfidf = models.TfidfModel(corpus)
	# tfidf_corpus = tfidf[corpus]
	return corpus # tfidf_corpus

def merge_documents(corpus, dictionary, docs_ids):
	'''
	Merge documents with same doc_id in the corpus according to docs_ids.
	The function will return the merged corpus and merged docs_ids.
	'''
	# # References:
	# # - How to sort a list and reorder a list according to indices?
	# #   https://stackoverflow.com/questions/6422700/how-to-get-indices-of-a-sorted-array-in-python/6423325
	# #   https://stackoverflow.com/questions/2177590/how-can-i-reorder-a-list
	# # - How to group by data by their keys?
	# #   https://docs.python.org/2/library/itertools.html#itertools.groupby
	# # TODO: Make this function more efficient in the future.
	# dense_corpus   = corpus2dense(corpus, num_terms=len(dictionary)).transpose()
	ordered_indice     = np.argsort(docs_ids)
	reordered_docs_ids = [ docs_ids[index] for index in ordered_indice ]
	# reordered_dense_corpus = [ dense_corpus[index] for index in ordered_indice ]
	# reordered_key_values   = zip(reordered_docs_ids, reordered_dense_corpus)
	# merged_key_values      = [
	# 	[ key_value[0], np.array(list(zip(*list(key_value[1])))[1]).sum(axis=0) ]
	# 	for key_value in itertools.groupby(reordered_key_values, lambda x: x[0]) ]
	# merged_key_values   = list(zip(*merged_key_values))
	# merged_docs_ids     = merged_key_values[0]
	# merged_dense_corpus = np.array(merged_key_values[1])
	# merged_corpus       = Dense2Corpus(merged_dense_corpus, documents_columns=False)
	# return merged_docs_ids, merged_corpus

	sparse_corpus           = corpus2csc(corpus, num_terms=len(dictionary)).transpose()
	reordered_sparse_corpus = sparse_corpus[ordered_indice, :]
	
	print(reordered_sparse_corpus.shape)


def corpus_histogram(corpus, dictionary, sort_by='weighted_sum', \
                     show=False, N=10, file_name='results/test.pdf', title=None):
	'''
	Calculate the histogram for each of the ngrams that appears in the indicated
	corpus.
	'''
	# target corpus with ngrams being sorted by their tfidf values
	sorted_corpus = [ sorted(doc, key=lambda x: -x[1]) for doc in corpus ]
	# distributions of each of ngrams in the corpus
	ngram_dist   = defaultdict(lambda: [])
	# build dict for distributions of each of ngrams (key=ngram_id, val=list of tfidf values)
	for doc in sorted_corpus:
		for ngram_id, tfidf_val in doc:
			ngram_dist[dictionary[ngram_id]].append(tfidf_val)
	# filter the ngrams which have less than one tfidf value
	lowfreq_ngrams = [ ngram
		for ngram, tfidf_set in ngram_dist.iteritems()
		if len(tfidf_set) < 2 ]
	for ngram in lowfreq_ngrams:
		ngram_dist.pop(ngram)
	# target of sorting indicated by input parameter
	sort_target = []
	if sort_by == 'count':
		# count of each of ngrams in the corpus
		sort_target = [ [ ngram, len(tfidf_set) ]
			for ngram, tfidf_set in ngram_dist.iteritems() ]
	elif sort_by == 'weighted_sum':
		# weighted sum of each of ngrams in the corpus
		sort_target = [ [ ngram, sum(tfidf_set) ]
			for ngram, tfidf_set in ngram_dist.iteritems() ]
	# sorted ngrams
	sorted_ngram = sorted(sort_target, key=lambda x: -x[1])[:N]
	# visualize the distributions for top N ngrams
	if show:
		import seaborn as sns
		with PdfPages(file_name) as pdf:
			fig, ax = plt.subplots(1, 1)
			sns.set(color_codes=True)
			for ngram, value in sorted_ngram:
				sns.distplot(ngram_dist[ngram],
					hist=False, rug=False, ax=ax, label='%s (%f)' % (ngram, value))
			ax.set(xlabel='tfidf value', ylabel='frequency (count)')
			if title is not None:
				ax.set_title(title, fontweight='bold')
			ax.legend()
			pdf.savefig(fig)
	return dict(ngram_dist), sorted_ngram
