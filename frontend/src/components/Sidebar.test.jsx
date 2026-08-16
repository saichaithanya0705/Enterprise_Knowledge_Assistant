import { render, screen } from "@testing-library/react";
import { Sidebar } from "./Sidebar";

function renderSidebar(overrides = {}) {
  return render(
    <Sidebar
      page="chat"
      onNavigate={() => {}}
      conversations={[]}
      activeConversationId={null}
      onSelectConversation={() => {}}
      onNewChat={() => {}}
      onDeleteConversation={() => {}}
      {...overrides}
    />,
  );
}

test("hides document library and admin control from normal users", () => {
  renderSidebar({ isAdmin: false, user: { name: "Member", role: "USER" } });

  expect(screen.queryByRole("button", { name: "Document library" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Admin control" })).not.toBeInTheDocument();
});

test("shows document library and admin control to administrators", () => {
  renderSidebar({ isAdmin: true, user: { name: "Administrator", role: "ADMIN" } });

  expect(screen.getByRole("button", { name: "Document library" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Admin control" })).toBeInTheDocument();
});

test("does not present configured-but-unverified providers as live", () => {
  render(
    <Sidebar
      page="chat"
      onNavigate={() => {}}
      conversations={[]}
      activeConversationId={null}
      onSelectConversation={() => {}}
      onNewChat={() => {}}
      onDeleteConversation={() => {}}
      chatBackend="configured_unverified"
      embeddingBackend="local_fallback"
      rerankBackend="configured_unverified"
    />,
  );

  expect(screen.getByTestId("provider-status")).toHaveTextContent(/configured/i);
  expect(screen.getByTestId("provider-status")).not.toHaveTextContent(/live|connected/i);
});

test("renders legacy configured provider values as unverified, never live", () => {
  render(
    <Sidebar
      page="chat"
      onNavigate={() => {}}
      conversations={[]}
      activeConversationId={null}
      onSelectConversation={() => {}}
      onNewChat={() => {}}
      onDeleteConversation={() => {}}
      chat_backend="key_gateway"
      embedding_backend="nvidia"
      rerank_backend="local_fallback"
    />,
  );

  expect(screen.getByTestId("provider-status")).toHaveTextContent("chat: configured (unverified)");
  expect(screen.getByTestId("provider-status")).toHaveTextContent("embeddings: configured (unverified)");
  expect(screen.getByTestId("provider-status")).not.toHaveTextContent(/live|connected/);
  expect(screen.getByTestId("provider-status")).toHaveTextContent("rerank: local fallback");
});

test("warns when semantic index coverage is incomplete", () => {
  render(
    <Sidebar
      page="chat"
      onNavigate={() => {}}
      conversations={[]}
      activeConversationId={null}
      onSelectConversation={() => {}}
      onNewChat={() => {}}
      onDeleteConversation={() => {}}
      chatBackend="local_fallback"
      embeddingBackend="nvidia"
      rerankBackend="nvidia"
      indexStatus={{
        index_status: "reingest_required",
        reingest_required: true,
        historical_generations_present: true,
        pending_action: "reingest",
      }}
    />,
  );

  expect(screen.getByRole("alert")).toHaveTextContent(/reingest/i);
  expect(screen.getByTestId("index-status")).toHaveTextContent("reingest_required");
});

test("renders conversation selection as a sibling button to delete", () => {
  render(
    <Sidebar
      page="chat"
      onNavigate={() => {}}
      conversations={[{ id: "c-1", title: "Leave policy" }]}
      activeConversationId={null}
      onSelectConversation={() => {}}
      onNewChat={() => {}}
      onDeleteConversation={() => {}}
    />,
  );

  const select = screen.getByRole("button", { name: "Open conversation Leave policy" });
  const remove = screen.getByRole("button", { name: "Delete conversation Leave policy" });
  expect(select).not.toContainElement(remove);
});

test("keeps conversation deletion visible for keyboard focus", () => {
  render(
    <Sidebar
      page="chat"
      onNavigate={() => {}}
      conversations={[{ id: "c-1", title: "Leave policy" }]}
      activeConversationId={null}
      onSelectConversation={() => {}}
      onNewChat={() => {}}
      onDeleteConversation={() => {}}
    />,
  );

  const remove = screen.getByRole("button", { name: "Delete conversation Leave policy" });
  expect(remove).toHaveClass("group-focus-within:opacity-100");
  expect(remove).toHaveClass("focus-visible:opacity-100");
});
