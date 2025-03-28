const { SESClient, SendEmailCommand } = require("@aws-sdk/client-ses");
const { fromEnv } = require("@aws-sdk/credential-providers");

const REGION = "us-east-2";
const SENDER_EMAIL = "furbreeze_synack@proton.me";
const BATCH_SIZE = 50; // AWS SES has a rate limit of 50 emails per second
const DELAY_BETWEEN_BATCHES = 1000; // 1 second delay between batches

const sesClient = new SESClient({ region: REGION, credentials: fromEnv() });

// Validate email address format
const isValidEmail = (email) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

// Sleep function for rate limiting
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

const sendEmail = async (toAddr, subject = "Test Email", htmlContent = null, textContent = null) => {
  if (!isValidEmail(toAddr)) {
    throw new Error(`Invalid email address: ${toAddr}`);
  }

  const params = {
    Destination: {
      ToAddresses: [toAddr],
    },
    Message: {
      Body: {
        Html: {
          Charset: "UTF-8",
          Data: htmlContent || "<html><body><p>This is a test email from AWS SES!</p></body></html>",
        },
        Text: {
          Charset: "UTF-8",
          Data: textContent || "This is a test email from AWS SES.",
        },
      },
      Subject: {
        Charset: "UTF-8",
        Data: subject,
      },
    },
    Source: SENDER_EMAIL,
  };

  try {
    const data = await sesClient.send(new SendEmailCommand(params));
    console.log(`Email sent successfully to ${toAddr}:`, data.MessageId);
    return data.MessageId;
  } catch (err) {
    console.error(`Error sending email to ${toAddr}:`, err.message);
    throw err;
  }
};

const sendBatchEmails = async (emailList, subject, htmlContent, textContent) => {
  const results = {
    successful: [],
    failed: [],
  };

  // Process emails in batches to respect rate limits
  for (let i = 0; i < emailList.length; i += BATCH_SIZE) {
    const batch = emailList.slice(i, i + BATCH_SIZE);
    const batchPromises = batch.map(email => 
      sendEmail(email, subject, htmlContent, textContent)
        .then(messageId => results.successful.push({ email, messageId }))
        .catch(error => results.failed.push({ email, error: error.message }))
    );

    await Promise.all(batchPromises);
    
    // Add delay between batches if not the last batch
    if (i + BATCH_SIZE < emailList.length) {
      await sleep(DELAY_BETWEEN_BATCHES);
    }
  }

  return results;
};

// Main execution
const main = async () => {
  // Get email addresses from command line arguments
  const emailList = process.argv.slice(2);
  
  if (emailList.length === 0) {
    console.error("Please provide at least one email address as a command line argument");
    process.exit(1);
  }

  // Validate all email addresses first
  const invalidEmails = emailList.filter(email => !isValidEmail(email));
  if (invalidEmails.length > 0) {
    console.error("Invalid email addresses found:", invalidEmails.join(", "));
    process.exit(1);
  }

  try {
    console.log(`Starting to send emails to ${emailList.length} recipients...`);
    const results = await sendBatchEmails(
      emailList,
      "Test Email",
      "<html><body><p>This is a test email from AWS SES!</p></body></html>",
      "This is a test email from AWS SES."
    );

    console.log("\nResults Summary:");
    console.log(`Successfully sent: ${results.successful.length}`);
    console.log(`Failed: ${results.failed.length}`);

    if (results.failed.length > 0) {
      console.log("\nFailed emails:");
      results.failed.forEach(({ email, error }) => {
        console.log(`${email}: ${error}`);
      });
    }
  } catch (error) {
    console.error("Fatal error:", error.message);
    process.exit(1);
  }
};

main();