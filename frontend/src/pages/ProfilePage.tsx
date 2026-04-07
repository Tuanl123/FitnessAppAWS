import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { format } from "date-fns";
import { getProfile, updateProfile } from "../api/users";

const INPUT_CLS = "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-base text-gray-900 disabled:bg-gray-50 disabled:text-gray-500 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:disabled:bg-gray-800 dark:disabled:text-gray-500 sm:text-sm";

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: getProfile,
    staleTime: 60_000,
  });

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [weight, setWeight] = useState("");
  const [goals, setGoals] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (profile) {
      setName(profile.name);
      setAge(profile.age?.toString() ?? "");
      setWeight(profile.weight?.toString() ?? "");
      setGoals(profile.fitness_goals ?? "");
    }
  }, [profile]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await updateProfile({
        name,
        age: age ? parseInt(age) : undefined,
        weight: weight ? parseFloat(weight) : undefined,
        fitness_goals: goals || undefined,
      });
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Profile updated!");
      setEditing(false);
    } catch {
      toast.error("Failed to update profile.");
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    if (profile) {
      setName(profile.name);
      setAge(profile.age?.toString() ?? "");
      setWeight(profile.weight?.toString() ?? "");
      setGoals(profile.fitness_goals ?? "");
    }
    setEditing(false);
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-teal-600 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Profile</h1>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            Edit
          </button>
        )}
      </div>

      <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-sm ring-1 ring-gray-100 dark:bg-gray-900 dark:ring-gray-800">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Name</label>
            <input type="text" disabled={!editing} value={name} onChange={(e) => setName(e.target.value)} className={INPUT_CLS} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Email</label>
            <input type="email" disabled value={profile?.email ?? ""} className="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-base text-gray-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-500 sm:text-sm" />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Age</label>
              <input type="number" disabled={!editing} min="13" max="120" value={age} onChange={(e) => setAge(e.target.value)} className={INPUT_CLS} />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Weight (kg)</label>
              <input type="number" disabled={!editing} step="0.1" min="20" max="500" value={weight} onChange={(e) => setWeight(e.target.value)} className={INPUT_CLS} />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Fitness Goals</label>
            <textarea disabled={!editing} rows={3} maxLength={500} value={goals} onChange={(e) => setGoals(e.target.value)} className={INPUT_CLS} placeholder="Describe your fitness goals..." />
          </div>

          {editing && (
            <div className="flex gap-3">
              <button type="submit" disabled={saving} className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50">
                {saving ? "Saving..." : "Save"}
              </button>
              <button type="button" onClick={handleCancel} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800">
                Cancel
              </button>
            </div>
          )}
        </form>

        {profile?.created_at && (
          <p className="mt-6 text-xs text-gray-400 dark:text-gray-500">
            Member since {format(new Date(profile.created_at), "MMMM d, yyyy")}
          </p>
        )}
      </div>
    </div>
  );
}
