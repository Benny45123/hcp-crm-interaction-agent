import { Provider } from 'react-redux';
import { store } from './store';
import InteractionForm from './components/InteractionForm';
import ChatPanel from './components/ChatPanel';

export default function App() {
  return (
    <Provider store={store}>
      <div className="app-layout">
        <div className="form-panel">
          <div className="form-panel-header">
            <h1>HCP Interaction Log</h1>
            <span className="header-badge">
              AI-mediated &middot; Read-only form
            </span>
          </div>
          <InteractionForm />
        </div>
        <div className="chat-panel">
          <ChatPanel />
        </div>
      </div>
    </Provider>
  );
}
