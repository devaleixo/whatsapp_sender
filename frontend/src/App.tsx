import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Campaigns from "./pages/Campaigns";
import CampaignDetail from "./pages/CampaignDetail";
import Templates from "./pages/Templates";
import RecipientTypes from "./pages/RecipientTypes";
import Queue from "./pages/Queue";
import Inbox from "./pages/Inbox";
import BotConfig from "./pages/BotConfig";
import Instance from "./pages/Instance";
import SettingsPage from "./pages/Settings";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/types" element={<RecipientTypes />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/campaigns" element={<Campaigns />} />
        <Route path="/campaigns/:id" element={<CampaignDetail />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/inbox" element={<Inbox />} />
        <Route path="/inbox/:contactId" element={<Inbox />} />
        <Route path="/bot" element={<BotConfig />} />
        <Route path="/instance" element={<Instance />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}
