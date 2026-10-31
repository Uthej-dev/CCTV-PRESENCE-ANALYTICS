import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui";

export default function NotFoundPage() {
  return <EmptyState title="Page not found" action={<Link className="btn" to="/">Go to dashboard</Link>}>The page you're looking for doesn't exist.</EmptyState>;
}
