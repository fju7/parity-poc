import { useState, useCallback, useRef } from "react";
import { Footer } from "./UploadView.jsx";

const ACCEPTED_TYPES = "image/jpeg,image/png,image/heic,image/webp";

export default function ImageUploadView({ onSubmit, onBack }) {
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const addFiles = useCallback((newFiles) => {
    const validFiles = Array.from(newFiles).filter((f) =>
      f.type.startsWith("image/")
    );
    if (validFiles.length === 0) {
      setError("Please select an image file (JPEG, PNG, HEIC, or WebP).");
      return;
    }
    setError("");

    // Generate previews
    validFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreviews((prev) => [...prev, { name: file.name, url: e.target.result }]);
      };
      reader.readAsDataURL(file);
    });

    setFiles((prev) => [...prev, ...validFiles]);
  }, []);

  const handleFileInput = useCallback(
    (e) => {
      if (e.target.files?.length) addFiles(e.target.files);
      e.target.value = "";
    },
    [addFiles]
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
  }, []);

  const removeFile = useCallback((index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (files.length === 0) return;
    setError("");
    setSubmitting(true);

    try {
      // Convert images to base64
      const base64Pages = await Promise.all(
        files.map(async (file) => {
          // Convert to JPEG via canvas for consistent format
          const bitmap = await createImageBitmap(file);
          const canvas = document.createElement("canvas");
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
          const ctx = canvas.getContext("2d");
          ctx.drawImage(bitmap, 0, 0);
          bitmap.close();

          const dataUrl = canvas.toDataURL("image/jpeg", 0.85);
          return dataUrl.split(",")[1]; // Strip prefix
        })
      );

      await onSubmit(base64Pages);
    } catch (err) {
      console.error("Image upload error:", err);
      setSubmitting(false);
      setError("Something went wrong processing the image. Please try again.");
    }
  }, [files, onSubmit]);

  return (
    <div className="min-h-screen bg-white flex flex-col items-center px-4 pt-12 font-[Arial,sans-serif]">
      <div className="w-full max-w-2xl">
        {/* Back link */}
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1B3A5C] cursor-pointer mb-6"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Back
        </button>

        <h2 className="text-2xl font-bold text-[#1B3A5C] mb-1">
          Upload Bill Image
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          Upload a photo or screenshot of your itemized bill.
        </p>

        {/* Drop zone / file picker */}
        {files.length === 0 ? (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="border-2 border-dashed border-gray-200 hover:border-[#0D7377] rounded-xl p-12 text-center cursor-pointer transition-colors"
            onClick={() => fileInputRef.current?.click()}
          >
            <svg className="w-12 h-12 text-[#0D7377]/50 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" />
            </svg>
            <p className="text-sm font-semibold text-[#1B3A5C] mb-1">
              Drop an image here or click to browse
            </p>
            <p className="text-xs text-gray-400">
              JPEG, PNG, HEIC, or WebP
            </p>
          </div>
        ) : (
          <>
            {/* Preview grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
              {previews.map((preview, index) => (
                <div key={index} className="relative group rounded-lg overflow-hidden border border-gray-200">
                  <img
                    src={preview.url}
                    alt={preview.name}
                    className="w-full h-32 object-cover"
                  />
                  <button
                    onClick={() => removeFile(index)}
                    className="absolute top-1.5 right-1.5 w-6 h-6 bg-black/60 text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                    </svg>
                  </button>
                  <p className="absolute bottom-0 left-0 right-0 bg-black/50 text-white text-xs px-2 py-1 truncate">
                    {preview.name}
                  </p>
                </div>
              ))}

              {/* Add more button */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="h-32 border-2 border-dashed border-gray-200 rounded-lg flex flex-col items-center justify-center text-gray-400 hover:border-[#0D7377] hover:text-[#0D7377] cursor-pointer transition-colors"
              >
                <svg className="w-6 h-6 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                <span className="text-xs">Add page</span>
              </button>
            </div>
          </>
        )}

        {/* Hidden file inputs */}
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          multiple
          className="hidden"
          onChange={handleFileInput}
        />
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleFileInput}
        />

        {/* Camera button (useful on mobile) */}
        <div className="flex gap-3 mt-4 mb-6">
          <button
            onClick={() => cameraInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 text-sm text-[#0D7377] border border-[#0D7377] rounded-lg hover:bg-[#0D7377]/5 cursor-pointer transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0Z" />
            </svg>
            Take Photo
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Privacy note */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-6">
          <div className="flex items-start gap-2">
            <svg className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            <p className="text-xs text-amber-800">
              Your bill image will be sent to our AI service for text extraction. Only procedure codes and amounts are used for benchmark analysis. No personal health information is stored.
            </p>
          </div>
        </div>

        {/* Submit button */}
        <button
          onClick={handleSubmit}
          disabled={files.length === 0 || submitting}
          className="w-full py-3 text-sm font-semibold text-white bg-[#0D7377] rounded-lg hover:bg-[#0B6164] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {submitting ? "Processing..." : `Analyze ${files.length === 1 ? "Image" : `${files.length} Images`}`}
        </button>
      </div>

      <Footer />
    </div>
  );
}
