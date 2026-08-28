/**
 * The three things a frontend test has to say here.
 *
 * 1. A citation leads to its own source. That is the product's whole claim and
 *    nothing tested it.
 * 2. Asking a new question does not carry the old selection into the new
 *    answer (BEY-13). A person found this twice: the first manual pass missed
 *    it because the next answer had fewer citations than the stale index, so
 *    nothing matched and the step looked clean.
 * 3. Activating a citation from the keyboard does what a click does, and leaves
 *    the focus where the user put it (BEY-15).
 *
 * The component is driven through the real ApiContext rather than a mocked
 * module: submitting the form runs the component's own handleSubmit, which is
 * where the reset in (2) lives.
 */

import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import ApiContext from '../contexts/ApiContext';
import CleanFactInterface from './CleanFactInterface';

// Scoped to the source panel on purpose: the citation elements carry
// `focus:ring-primary` in their class list, so a looser selector matches them
// too and the test passes while measuring the wrong thing.
const ACTIVE_HIGHLIGHT = '[data-highlight-id][class*="ring-primary"]';

/** A highlight has to carry the offsets the renderer slices the chunk with. */
const highlightOf = (content, text) => ({
  text,
  start: content.indexOf(text),
  end: content.indexOf(text) + text.length,
});

const documentOf = (id, title, content, quoted) => ({
  title,
  source: `/app/${title}.md`,
  content,
  highlights: [highlightOf(content, quoted)],
  metadata: { document_id: id },
});

const README_TEXT = 'Add documents like this: index.add_documents([document]) and you are done.';
const GUIDE_TEXT = 'Documents are indexed using vector embeddings before retrieval.';
const README_QUOTE = 'index.add_documents([document])';
const GUIDE_QUOTE = 'Documents are indexed using vector embeddings';

const twoCitationAnswer = {
  question: 'How do I put documents into the index?',
  answer: 'Adding them is one call [1], and the index embeds them [2].',
  structured_answer: {
    text: 'Adding them is one call [1], and the index embeds them [2].',
    citations: [
      { text: README_QUOTE, doc_index: 0, highlight_index: 0, number: 1, type: 'display' },
      { text: GUIDE_QUOTE, doc_index: 1, highlight_index: 0, number: 2, type: 'display' },
    ],
  },
  documents: [
    documentOf('doc-readme', 'README', README_TEXT, README_QUOTE),
    documentOf('doc-guide', 'GUIDE', GUIDE_TEXT, GUIDE_QUOTE),
  ],
};

/** The second answer of the repeat-query test. It must carry at least as many
 * citations as the index left behind by the click, or the assertion passes for
 * the wrong reason — that is exactly how the first manual pass missed BEY-13. */
const laterAnswer = {
  question: 'What is a chunk?',
  answer: 'A chunk is a slice of a document [1], and it is what retrieval returns [2].',
  structured_answer: {
    text: 'A chunk is a slice of a document [1], and it is what retrieval returns [2].',
    citations: [
      { text: README_QUOTE, doc_index: 0, highlight_index: 0, number: 1, type: 'display' },
      { text: GUIDE_QUOTE, doc_index: 1, highlight_index: 0, number: 2, type: 'display' },
    ],
  },
  documents: [
    documentOf('doc-readme', 'README', README_TEXT, README_QUOTE),
    documentOf('doc-guide', 'GUIDE', GUIDE_TEXT, GUIDE_QUOTE),
  ],
};

/** Holds what the real provider holds, so the component's own submit path runs. */
const Harness = ({ answers }) => {
  const [index, setIndex] = useState(0);

  const value = {
    isLoading: false,
    isResourcesLoaded: true,
    documentCount: 2,
    currentQuery: answers[index],
    submitQuery: async () => setIndex((i) => Math.min(i + 1, answers.length - 1)),
    resetQuery: () => setIndex(0),
  };

  return (
    <ApiContext.Provider value={value}>
      <CleanFactInterface />
    </ApiContext.Provider>
  );
};

const renderWith = (...answers) => render(<Harness answers={answers} />);

const citation = (number) => screen.getByRole('button', { name: `Show citation ${number}` });

describe('a citation leads to its own source', () => {
  it('selects the document the citation came from', async () => {
    const user = userEvent.setup();
    const { container } = renderWith(twoCitationAnswer);

    await user.click(citation(2));

    expect(screen.getByText(/before retrieval/)).toBeInTheDocument();
    expect(container.querySelectorAll(ACTIVE_HIGHLIGHT)).toHaveLength(1);
  });

  it('marks the passage whose text is the one quoted in the answer', async () => {
    const user = userEvent.setup();
    const { container } = renderWith(twoCitationAnswer);

    await user.click(citation(2));

    // The marker class is the only observable of "this passage is the selected
    // one" — the component expresses the state nowhere else.
    expect(container.querySelector(ACTIVE_HIGHLIGHT)).toHaveTextContent(GUIDE_QUOTE);
  });

  it('moves the mark when a different citation is clicked', async () => {
    const user = userEvent.setup();
    const { container } = renderWith(twoCitationAnswer);

    await user.click(citation(2));
    expect(container.querySelector(ACTIVE_HIGHLIGHT)).toHaveTextContent(GUIDE_QUOTE);

    await user.click(citation(1));

    // Two clicks in one test on purpose: a lookup that always returned the same
    // fact would satisfy either assertion alone.
    expect(container.querySelector(ACTIVE_HIGHLIGHT)).toHaveTextContent(README_QUOTE);
    expect(container.querySelectorAll(ACTIVE_HIGHLIGHT)).toHaveLength(1);
  });
});

describe('a new question does not inherit the old selection', () => {
  it('leaves no passage marked in the answer that follows', async () => {
    const user = userEvent.setup();
    const staleIndex = 0;
    // Guard the test against itself: with fewer citations than the stale index,
    // nothing would match in the new answer and this would pass while broken.
    expect(laterAnswer.structured_answer.citations.length).toBeGreaterThan(staleIndex);

    const { container } = renderWith(twoCitationAnswer, laterAnswer);
    await user.click(citation(staleIndex + 1));
    expect(container.querySelectorAll(ACTIVE_HIGHLIGHT)).toHaveLength(1);

    await user.type(screen.getByRole('textbox'), 'What is a chunk?');
    await user.click(screen.getByRole('button', { name: 'Ask' }));

    expect(screen.getByText(/what retrieval returns/)).toBeInTheDocument();
    expect(container.querySelectorAll(ACTIVE_HIGHLIGHT)).toHaveLength(0);
  });
});

describe('a citation can be activated from the keyboard', () => {
  it('marks the same passage Enter as a click would', async () => {
    const user = userEvent.setup();
    const { container } = renderWith(twoCitationAnswer);

    citation(2).focus();
    await user.keyboard('{Enter}');

    expect(container.querySelector(ACTIVE_HIGHLIGHT)).toHaveTextContent(GUIDE_QUOTE);
  });

  it('answers Space as well, which a link would not', async () => {
    const user = userEvent.setup();
    const { container } = renderWith(twoCitationAnswer);

    citation(2).focus();
    await user.keyboard('{ }');

    expect(container.querySelector(ACTIVE_HIGHLIGHT)).toHaveTextContent(GUIDE_QUOTE);
  });

  it('leaves the focus on the citation that was activated', async () => {
    const user = userEvent.setup();
    renderWith(twoCitationAnswer);

    const target = citation(2);
    target.focus();
    await user.keyboard('{Enter}');

    // Not a style question: the element is only still focused if React
    // reconciled the answer instead of remounting it. BEY-15 was that remount.
    expect(document.activeElement).toBe(target);
  });
});
