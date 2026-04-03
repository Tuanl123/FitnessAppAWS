import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const strength =
    password.length === 0
      ? null
      : password.length < 8
        ? "weak"
        : /[A-Z]/.test(password) && /[a-z]/.test(password) && /\d/.test(password)
          ? "strong"
          : "medium";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await register(email, password, name);
      navigate("/");
    } catch {
      setError("Registration failed. Email may already be in use.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4 dark:bg-gray-950">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-md dark:bg-gray-900">
        <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-gray-100">Create account</h1>
        <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
          Start tracking your fitness metrics
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm"
              placeholder="John Doe"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm"
              placeholder="********"
            />
            {strength && (
              <div className="mt-2 flex gap-1">
                <div className={`h-1 flex-1 rounded ${strength === "weak" ? "bg-red-400" : strength === "medium" ? "bg-amber-400" : "bg-green-400"}`} />
                <div className={`h-1 flex-1 rounded ${strength === "medium" ? "bg-amber-400" : strength === "strong" ? "bg-green-400" : "bg-gray-200 dark:bg-gray-700"}`} />
                <div className={`h-1 flex-1 rounded ${strength === "strong" ? "bg-green-400" : "bg-gray-200 dark:bg-gray-700"}`} />
              </div>
            )}
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Confirm Password</label>
            <input
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 sm:text-sm"
              placeholder="********"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-teal-600 hover:underline dark:text-teal-400">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
