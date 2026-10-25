import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { RequireAuth, RedirectIfAuthed } from "./auth/RequireAuth";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Signup } from "./pages/Signup";
import { Dashboard } from "./pages/Dashboard";
import { Problems } from "./pages/Problems";
import { Revision } from "./pages/Revision";
import { Recommendations } from "./pages/Recommendations";
import { Notebook } from "./pages/Notebook";
import { Settings } from "./pages/Settings";
import { History } from "./pages/History";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<RedirectIfAuthed />}>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
          </Route>

          <Route element={<RequireAuth />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/problems" element={<Problems />} />
              <Route path="/revision" element={<Revision />} />
              <Route path="/recommendations" element={<Recommendations />} />
              <Route path="/notebook" element={<Notebook />} />
              <Route path="/notebook/:problemId" element={<Notebook />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/history" element={<History />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
