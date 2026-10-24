import { ImageResponse } from "next/og";

export const alt = "Applyon — AI Job Applications for India";
export const size = {
  width: 1200,
  height: 630,
};
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#07070A",
          backgroundImage:
            "radial-gradient(circle at 50% 30%, rgba(79, 70, 229, 0.25), transparent 70%)",
          color: "#ffffff",
          fontFamily: "sans-serif",
          padding: "60px 80px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            backgroundColor: "rgba(255, 255, 255, 0.08)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            borderRadius: "999px",
            padding: "10px 24px",
            marginBottom: "32px",
          }}
        >
          <span style={{ fontSize: "24px", fontWeight: 700, color: "#F5A524" }}>*</span>
          <span
            style={{
              fontSize: "24px",
              fontWeight: 700,
              letterSpacing: "-0.03em",
            }}
          >
            Applyon
          </span>
        </div>

        <h1
          style={{
            fontSize: "64px",
            fontWeight: 800,
            lineHeight: 1.1,
            letterSpacing: "-0.04em",
            margin: "0 0 20px 0",
          }}
        >
          Apply smarter. Interview sooner.
        </h1>

        <p
          style={{
            fontSize: "26px",
            color: "#A1A1AA",
            maxWidth: "800px",
            margin: "0",
            lineHeight: 1.4,
          }}
        >
          AI-powered job applications for India. Tailor your resume, autofill forms, and manage your job hunt.
        </p>
      </div>
    ),
    {
      ...size,
    }
  );
}
