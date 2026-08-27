import { ApiProvider } from './contexts/ApiContext';
import CleanFactInterface from './components/CleanFactInterface';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <ApiProvider>
        <CleanFactInterface />
      </ApiProvider>
    </ErrorBoundary>
  );
}

export default App;
