import React from 'react';
import { conf } from '../config/conf';
import { Link } from 'react-router-dom';

const PrivacyPolicy = () => {
  const supportEmail = conf.emailAddress || '[Your Support Email Address]';
  const mailtoLink = `mailto:${supportEmail}`;

  return (
    <div className="bg-[#1C221C] text-white min-h-screen p-4 sm:p-8">
      <div className="max-w-4xl mx-auto bg-[#0A363CB2] p-6 sm:p-10 rounded-lg border border-cyan-900">
        <div className="mb-8 text-center">
          <h1 className="text-3xl sm:text-4xl font-bold text-[#13E3FF] mb-2">Privacy Policy for Rapid Answer Generator</h1>
          <p className="text-gray-400">Last Updated: October 26, 2025</p>
        </div>

        <div className="space-y-6 text-gray-300 leading-relaxed">
          <p>
            This Privacy Policy explains how Rapid Answer Generator ("the App," "we," "us," or "our") collects, uses, and shares your information when you use our services.
          </p>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">1. Data We Collect</h2>
            <p>
              When you sign in to Rapid Answer Generator using your Google Account, we collect the following information from your profile:
            </p>
            <ul className="list-disc list-inside pl-4 mt-2 space-y-1">
              <li>Your full name</li>
              <li>Your email address</li>
              <li>Your profile picture</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">2. How We Use Your Data</h2>
            <p>
              We use the data we collect for the following purposes:
            </p>
            <ul className="list-disc list-inside pl-4 mt-2 space-y-1">
              <li>To create and manage your user account.</li>
              <li>To personalize your experience within the app.</li>
              <li>To provide core functionality of the application.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">3. How We Store Your Data</h2>
            <p>
              The information you provide is stored securely on our servers, which are managed by Appwrite Cloud and located in Frankfurt, Germany. We take reasonable measures to protect your data from unauthorized access or disclosure.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">4. Data Sharing and Disclosure</h2>
            <p>
              We do not sell, rent, or trade your personal data to third parties.
            </p>
            <p>
              We may share your data with third-party service providers only as necessary to provide our services. For example, we use Appwrite Cloud to store your data. These third parties are bound by strict confidentiality obligations.
            </p>
            <p>
              We may also disclose your information if required by law, such as to comply with a subpoena or other legal process.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">5. Compliance with Google API Services User Data Policy</h2>
            <p>
              Rapid Answer Generator's use of information received from Google APIs will adhere to the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-cyan-500 hover:underline">Google API Services User Data Policy</a>, including the Limited Use requirements.
            </p>
            <p>
              Specifically, we will only use Google user data for providing or improving user-facing features that are clearly visible to you. We will not use the data for:
            </p>
            <ul className="list-disc list-inside pl-4 mt-2 space-y-1">
              <li>Serving advertisements.</li>
              <li>Transferring, selling, or sharing your data with any third party for any purpose not directly related to providing our services.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">6. Your Rights</h2>
            <p>
              You have the right to access, update, or delete your personal information. If you wish to do so, please contact us at <a href={mailtoLink} className="text-cyan-500 hover:underline">{supportEmail}</a>.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">7. Changes to this Privacy Policy</h2>
            <p>
              We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the "Last Updated" date.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold text-cyan-400 mb-3">8. Contact Us</h2>
            <p>
              If you have any questions about this Privacy Policy, please contact us at: <a href={mailtoLink} className="text-cyan-500 hover:underline">{supportEmail}</a>.
            </p>
          </section>
        </div>
        <div className="mt-8 text-center">
            <Link to="/" className="text-cyan-400 hover:text-cyan-300 transition-colors">&larr; Back to Home</Link>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;