<?php
// Start output buffering
ob_start();

// Get form values
$name = $_POST['name'] ?? '';
$visitor_email = $_POST['email'] ?? '';
$subject = $_POST['subject'] ?? '';
$message = $_POST['message'] ?? '';

// Validate required fields
if (empty($name) || empty($visitor_email) || empty($message)) {
    die("Please fill all required fields.");
}

// Email setup
$email_from = 'info@website.com';
$email_subject = 'New Form Submission';
$email_body = "User Name: $name\n".
              "User Email: $visitor_email\n".
              "Subject: $subject\n".
              "User Message: $message\n";

$to = 'ethical455@gmail.com';

// Correct headers
$headers  = "From: $email_from\r\n";
$headers .= "Reply-To: $visitor_email\r\n";

// Send mail
mail($to, $email_subject, $email_body, $headers);

// Redirect
header("Location: contact.html");
echo "<pre>";
print_r($_POST);
echo "</pre>";
exit();

ob_end_flush();
?>
