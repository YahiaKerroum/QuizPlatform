import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default function HomePage() {
  const token = cookies().get("token")?.value;
  redirect(token ? "/dashboard" : "/login");
}

