import OracleAgentHub from "./OracleAgentHub";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Login from "./auth/Login";

function Application() {
  const { token } = useAuth();
  return token ? <OracleAgentHub /> : <Login />;
}

function App() {
  return (
    <AuthProvider>
      <Application />
    </AuthProvider>
  );
}

export default App;
